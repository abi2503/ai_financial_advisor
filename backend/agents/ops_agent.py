"""
Alex Ops Agent — Production AIOps + FinOps + LLM Observability
Full observability: costs, traces, tool calls, API costs, rate limits
"""
import os
import json
import boto3
import logging
import urllib.request
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
UTC    = timezone.utc

REGION         = os.environ.get('AWS_REGION', 'us-east-1')
ACCOUNT_ID     = os.environ.get('ACCOUNT_ID', '381491881089')
CLUSTER_ARN    = os.environ.get('DB_CLUSTER_ARN', '')
SECRET_ARN     = os.environ.get('DB_SECRET_ARN', '')
DB_NAME        = os.environ.get('DB_NAME', 'alex_db')
ALERT_EMAIL    = os.environ.get('ALERT_EMAIL', 'abhishek.suresh2503@gmail.com')
FROM_EMAIL     = os.environ.get('FROM_EMAIL', 'abhishek.suresh2503@gmail.com')
FRONTEND_URL   = os.environ.get('FRONTEND_URL', 'https://ai-financial-advisor-t6kt-abi2503s-projects.vercel.app')
ALB_URL        = os.environ.get('ALB_URL', '')
COST_THRESHOLD = float(os.environ.get('DAILCOST_THRESHOLD', '10.0'))
AUTONOMOUS     = os.environ.get('AUTONOMOUS_MODE', 'false').lower() == 'true'

bedrock  = boto3.client('bedrock-runtime', region_name=REGION)
ecs_c    = boto3.client('ecs',             region_name=REGION)
sage_c   = boto3.client('sagemaker',       region_name=REGION)
ce       = boto3.client('ce',              region_name='us-east-1')
rds_data = boto3.client('rds-data',        region_name=REGION)
ses      = boto3.client('ses',             region_name=REGION)
ssm      = boto3.client('ssm',             region_name=REGION)
cw       = boto3.client('cloudwatch',      region_name=REGION)
cw_logs  = boto3.client('logs',            region_name=REGION)
sqs_c    = boto3.client('sqs',             region_name=REGION)
lambda_c = boto3.client('lambda',          region_name=REGION)

# ============================================
# Resource Registry
# ============================================
RESOURCES = {
    "ecs":       {"cluster": "alex-cluster", "service": "alex-researcher"},
    "sagemaker": {"endpoint": "alex-embedding"},
    "aurora":    {"cluster": "alex-aurora"},
    "lambdas": {
        "alex-planner":      "Planner",
        "alex-tagger":       "Tagger",
        "alex-reporter":     "Reporter",
        "alex-scheduler":    "Scheduler",
        "alex-cost-monitor": "Cost Monitor",
        "alex-ops-agent":    "Ops Agent"
    },
    "sqs": {
        "alex-research-queue":   "Research tasks",
        "alex-results-queue":    "Reporter trigger",
        "alex-frontend-results": "Frontend polling",
        "alex-dlq":              "Dead letter"
    }
}

# External API costs (estimated per call)
EXTERNAL_API_COSTS = {
    "yahoo_finance":    {"cost_per_call": 0.0,    "description": "yfinance (free)"},
    "sec_edgar":        {"cost_per_call": 0.0,    "description": "SEC EDGAR (free)"},
    "marketbeat":       {"cost_per_call": 0.0,    "description": "MarketBeat (scraped)"},
    "unusual_whales":   {"cost_per_call": 0.0,    "description": "UnusualWhales (scraped)"},
    "bedrock_nova_pro": {"cost_per_1k_in": 0.0008, "cost_per_1k_out": 0.0032,
                         "description": "Nova Pro — research generation"},
    "bedrock_nova_lite":{"cost_per_1k_in": 0.00006,"cost_per_1k_out": 0.00024,
                         "description": "Nova Lite — classification/ops"},
    "sagemaker_embed":  {"cost_per_1k": 0.0001,  "description": "all-MiniLM-L6-v2 serverless"},
}


# ============================================
# CloudWatch Metrics Emitter
# ============================================
def emit_metric(name, value, unit='Count', dimensions=None):
    try:
        dims = [{'Name': 'Agent', 'Value': 'alex-ops-agent'}]
        if dimensions:
            for k, v in dimensions.items():
                dims.append({'Name': k, 'Value': str(v)})
        cw.put_metric_data(
            Namespace  = 'AlexAI/Ops',
            MetricData = [{
                'MetricName': name,
                'Value':      value,
                'Unit':       unit,
                'Dimensions': dims,
                'Timestamp':  datetime.now(UTC)
            }]
        )
    except Exception as e:
        print(f"Metric emit error: {e}")


# ============================================
# Agent Traces + Tool Call Analysis
# ============================================
def get_agent_traces(hours=24):
    """
    Pull agent execution traces from CloudWatch Logs.
    Extracts: tool calls, latency per tool, success rates,
    which tools are called most, agent turn counts.
    """
    try:
        end   = datetime.now(UTC)
        start = end - timedelta(hours=hours)

        traces = {
            "tool_calls":          {},
            "agent_runs":          0,
            "avg_turns":           0,
            "tool_success_rates":  {},
            "slowest_tools":       [],
            "most_used_tools":     [],
            "agent_errors":        0,
            "total_tool_calls":    0
        }

        # Search ECS logs for tool call patterns
        try:
            response = cw_logs.filter_log_events(
                logGroupName  = '/ecs/alex-researcher',
                startTime     = int(start.timestamp() * 1000),
                endTime       = int(end.timestamp() * 1000),
                filterPattern = 'Tool',
                limit         = 1000
            )

            tool_counts    = {}
            tool_errors    = {}
            agent_run_count = 0

            for event in response.get('events', []):
                msg = event.get('message', '')

                # Count agent runs
                if 'Alex-Data-Agent' in msg or 'Alex-Stream-Agent' in msg:
                    agent_run_count += 1

                # Count tool invocations
                tools = [
                    'get_stock_data',
                    'get_sec_filings',
                    'ingest_financial_document',
                    'get_news',
                    'web_search'
                ]
                for tool in tools:
                    if tool in msg:
                        tool_counts[tool] = tool_counts.get(tool, 0) + 1
                        if 'error' in msg.lower() or 'Error' in msg:
                            tool_errors[tool] = tool_errors.get(tool, 0) + 1

            traces['tool_calls']       = tool_counts
            traces['agent_runs']       = agent_run_count
            traces['total_tool_calls'] = sum(tool_counts.values())
            traces['most_used_tools']  = sorted(
                tool_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]

            # Calculate success rates
            for tool, count in tool_counts.items():
                errors = tool_errors.get(tool, 0)
                traces['tool_success_rates'][tool] = round(
                    ((count - errors) / max(count, 1)) * 100, 1
                )

        except Exception as e:
            print(f"Traces log error: {e}")

        # Lambda traces — planner task decomposition
        try:
            response = cw_logs.filter_log_events(
                logGroupName  = '/aws/lambda/alex-planner',
                startme     = int(start.timestamp() * 1000),
                endTime       = int(end.timestamp() * 1000),
                filterPattern = 'Tasks queued',
                limit         = 100
            )
            planner_runs = len(response.get('events', []))
            traces['planner_runs'] = planner_runs

            # Extract avg tasks per run
            task_counts = []
            for event in response.get('events', []):
                msg = event.get('message', '')
                if 'queued' in msg:
                    try:
                        num = int(''.join(filter(str.isdigit, msg.split('queued')[0][-3:])))
                        if 0 < num < 20:
                            task_counts.append(num)
                    except Exception:
                        pass
            traces['avg_tasks_per_plan'] = round(
                sum(task_counts) / max(len(task_counts), 1), 1
            ) if task_counts else 0

        except Exception as e:
            print(f"Planner traces error: {e}")

        # Reporter traces
        try:
            response = cw_logs.filter_log_events(
                logGroupName  = '/aws/lambda/alex-reporter',
                startTime     = int(start.timestamp() * 1000),
                endTime       = int(end.timestamp() * 1000),
                filterPattern = 'Report generated',
                limit         = 200
            )
            reporter_runs = len(response.get('events', []))
            traces['reporter_runs'] = reporter_runs

        except Exception as e:
            print(f"Reporter traces error: {e}")

        # Emit trace metrics
        emit_metric('TotalToolCalls',   traces['total_tool_calls'])
        emit_metric('AgentRuns',        traces['agent_runs'])
        emit_metric('PlannerRuns',      traces.get('planner_runs', 0))
        emit_metric('ReporterRuns',     traces.get('reporter_runs', 0))

        return traces

    except Exception as e:
        print(f"Agent traces error: {e}")
        return {}


# ============================================
# External API Cost Tracker
# ============================================
def get_external_api_costs(hours=24):
    """
    Track calls to external APIs and estimate costs.
    Sources: Yahoo Finance, SEC EDGAR, MarketBeat,
             UnusualWhales, Bedrock, SageMaker
    """
    try:
        end   = datetime.now(UTC)
        start = end - timedelta(hours=hours)

        api_costs = {
            "breakdown": {},
            "total_external_cost": 0.0,
            "total_aws_cost":      0.0,
            "call_counts":         {}
        }

        # Count tool calls from ECS logs
        tool_to_api = {
            "get_stock_data":          "yahoo_finance",
            "get_sec_filings":         "sec_edgar",
            "get_news":                "yahoo_finance",
            "MarketBeat":              "marketbeat",
            "UnusualWhales":           "unusual_whales",
            "playwright":              "playwright_browser"
        }

        try:
            response = cw_logs.filter_log_events(
                logGroupName  = '/ecs/alex-researcher',
                startTime     = int(start.timestamp() * 1000),
                endTime       = int(end.timestamp() * 1000),
                limit         = 2000
            )

            for event in response.get('events', []):
                msg = event.get('message', '')
                for tool, api in tool_to_api.items():
                    if tool in msg:
                        api_costs['call_counts'][api] = \
                            api_costs['call_counts'].get(api, 0) + 1

        except Exception as e:
            print(f"API call count error: {e}")

        # Calculate costs
        for api, count in api_costs['call_counts'].items():
            api_info = EXTERNAL_API_COSTS.get(api, {})
            cost_per = api_info.get('cost_per_call', 0)
            total    = round(count * cost_per, 6)
            api_costs['breakdown'][api] = {
                "calls":       count,
                "cost":        total,
                "description": api_info.get('description', api)
            }
            api_costs['total_external_cost'] += total

        # Bedrock costs from CloudWatch metrics
        try:
            # Nova Pro invocations
            r = cw.get_metric_statistics(
                Namespace='AlexAI', MetricName='ResearchQuery',
                Dimensions=[{'Name': 'Service', 'Value': 'alex-researcher'}],
                StartTime=start, EndTime=end,
                Period=3600 * hours, Statistics=['Sum']
            )
            nova_pro_calls = int(sum(d['Sum'] for d in r['Datapoints']))

            # Estimate tokens (avg per research query)
            tokens_in  = nova_pro_calls * 600   # ~600 tokens input
            tokens_out = nova_pro_calls * 900   # ~900 tokens output
            nova_pro_cost = (tokens_in / 1000 * 0.0008) + \
                            (tokens_out / 1000 * 0.0032)

            api_costs['breakdown']['bedrock_nova_pro'] = {
                "calls":       nova_pro_calls,
                "tokens_in":   tokens_in,
                "tokens_out":  tokens_out,
                "cost":        round(nova_pro_cost, 4),
                "description": "Nova Pro — research generation"
            }
            api_costs['total_aws_cost'] += nova_pro_cost

        except Exception as e:
            print(f"Bedrock cost error: {e}")

        # Nova Lite (Tagger + Reporter + Ops)
        try:
            r = cw.get_metric_statistics(
                Namespace='AWS/Lambda', MetricName='Invocations',
                Dimensions=[{'Name': 'FunctionName', 'Value': 'alex-reporter'}],
                StartTime=start, EndTime=end,
                Period=3600 * hours, Statistics=['Sum']
            )
            reporter_calls = int(sum(d['Sum'] for d in r['Datapoints']))
            tokens_in      = reporter_calls * 300
            tokens_out     = reporter_calls * 400
            nova_lite_cost = (tokens_in / 1000 * 0.00006) + \
                             (tokens_out / 1000 * 0.00024)

            api_costs['bakdown']['bedrock_nova_lite'] = {
                "calls":       reporter_calls,
                "tokens_in":   tokens_in,
                "tokens_out":  tokens_out,
                "cost":        round(nova_lite_cost, 4),
                "description": "Nova Lite — reporter/ops/tagger"
            }
            api_costs['total_aws_cost'] += nova_lite_cost

        except Exception as e:
            print(f"Nova Lite cost error: {e}")

        # SageMaker embedding cost
        try:
            r = cw.get_metric_statistics(
                Namespace='AWS/SageMaker', MetricName='InvocationsPerInstance',
                Dimensions=[{'Name': 'EndpointName', 'Value': 'alex-embedding'}],
                StartTime=start, EndTime=end,
                Period=3600 * hours, Statistics=['Sum']
            )
            embed_calls = int(sum(d['Sum'] for d in r['Datapoints']))
            embed_cost  = (embed_calls / 1000) * 0.0001

            api_costs['breakdown']['sagemaker_embed'] = {
                "calls":     embed_calls,
                "cost":        round(embed_cost, 6),
                "description": "SageMaker all-MiniLM-L6-v2 serverless"
            }
            api_costs['total_aws_cost'] += embed_cost

        except Exception as e:
            print(f"SageMaker cost error: {e}")

        api_costs['total_external_cost'] = round(api_costs['total_external_cost'], 6)
        api_costs['total_aws_cost']      = round(api_costs['total_aws_cost'], 4)
        api_costs['grand_total']         = round(
            api_costs['total_external_cost'] + api_costs['total_aws_cost'], 4
        )

        # Emit cost metrics
        emit_metric('ExternalAPICost', api_costs['total_external_cost'], 'None')
        emit_metric('AWSAPICost',      api_costs['total_aws_cost'],      'None')
        emit_metric('TotalAPICallCost',api_costs['grand_total'],         'None')

        return api_costs

    except Exception as e:
        print(f"External API cost error: {e}")
        return {}


# ============================================
# LLM Observability
# ============================================
def get_llm_metrics(hours=24):
    try:
        end    = datetime.now(UTC)
        start  = end - timedelta(hours=hours)
        period = 3600 * hours

        raw = {}
        for metric_name, stat in [
            ('ResearchLatency', 'Average'),
            ('ResearchQuery',   'Sum'),
            ('ResearchError',   'Sum'),
            ('GuardrailBlock',  'Sum'),
        ]:
            try:
                r = cw.get_metric_statistics(
                    Namespace='AlexAI', MetricName=metric_name,
                    Dimensions=[{'Name': 'Service', 'Value': 'alex-researcher'}],
                    StartTime=start, EndTime=end,
                    Period=period, Statistics=[stat]
                )
                raw[metric_name] = r['Datapoints'][0][stat] if r['Datapoints'] else 0
            except Exception:
                raw[metric_name] = 0

        queries        = raw.get('ResearchQuery', 0)
        errors         = raw.get('ResearchError', 0)
        est_tokens_in  = queries * 600
        est_tokens_out = queries * 900
        llm_cost       = (est_tokens_in / 1000 * 0.0008) + \
                         (est_tokens_out / 1000 * 0.0032)

        out = {
            'TotalQueries':       int(queries),
            'TotalErrors':        int(errors),
            'GuardrailBlocks':    int(raw.get('GuardrailBlock', 0)),
            'AvgLatency':         round(raw.get('ResearchLatency', 0), 2),
            'EstimatedTokensIn':  int(est_tokens_in),
            'EstimatedTokensOut': int(est_tokens_out),
            'EstimatedLLMCost':   round(llm_cost, 4),
            'ErrorRate':          round((int(errors) / max(int(queries), 1)) * 100, 1),
            'CostPerQuery':       round(llm_cost / max(int(queries), 1), 4)
        }

        # Per-mode breakdown
        for mode in ['fast', 'deep', 'stream']:
            try:
                r = cw.get_metric_statistics(
                    Namespace='AlexAI', MetricName='ResearchLatency',
                    Dimensions=[
                        {'Name': 'Service', 'Value': 'alex-researcher'},
                        {'Name': 'Mode',    'Value': mode}
                    ],
                    StartTime=start, EndTime=end,
                    Period=period, Statistics=['Average']
                )
                out[f'{mode}_latency'] = round(
                    r['Datapoints'][0]['Average'] if r['Datapoints'] else 0, 2
                )
            except Exception:
                out[f'{mode}_latency'] = 0

        emit_metric('LLMQueriesTracked',  out['TotalQueries'])
        emit_metric('LLMErrorRate',       out['ErrorRate'],       'Percent')
        emit_metric('LLMAvgLatency',      out['AvgLatency'],      'Seconds')
        emit_metric('LLMEstimatedCost',   out['EstimatedLLMCost'],'None')
        emit_metric('LLMCostPerQuery',    out['CostPerQuery'],    'None')
        emit_metric('LLMTokensEstimated', est_tokens_in + est_tokens_out)

        return out
    except Exception as e:
        print(f"LLM metrics error: {e}")
        return {}


# ============================================
# API Call Tracking (Inbound + Outbound)
# ============================================
def get_api_metrics(hours=24):
    try:
        end   = datetime.now(UTC)
        start = end - timedelta(hours=hours)
        data  = {"inbound": {}, "outbound": {}, "alb": {}}

        # ALB
        try:
            r = cw.get_metric_statistics(
                Namespace='AWS/ApplicationELB', MetricName='RequestCount',
                Dimensions=[{'Name': 'LoadBalancer',
                             'Value': 'app/alex-alb/e9c1011892552042'}],
                StartTime=start, EndTime=end,
                Period=3600 * hours, Statistics=['Sum']
            )
            data['alb']['total_requests'] = int(sum(d['Sum'] for d in r['Datapoints']))
        except Exception:
            data['alb']['total_requests'] = 0

        for code in ['HTTPCode_ELB_4XX_Count', 'HTTPCode_ELB_5XX_Count']:
            try:
                r = cw.get_metric_statistics(
                    Namespace='AWS/ApplicationELB', MetricName=code,
                    Dimensions=[{'Name': 'LoadBalancer',
                                 'Value': 'app/alex-alb/e9c1011892552042'}],
                    StartTime=start, EndTime=end,
                    Period=3600 * hours, Statistics=['Sum']
                )
                data['alb'][code] = int(sum(d['Sum'] for d in r['Datapoints']))
            except Exception:
                data['alb'][code] = 0

        # Outbound from ECS logs
        try:
            r = cw_logs.filter_log_events(
                logGroupName='/ecs/alex-researcher',
                startTime=int(start.timestamp() * 1000),
                endTime=int(end.timestamp() * 1000),
                filterPattern='fetch', limit=100
            )
            data['outbound']['ecs_external_calls'] = len(r.get('events', []))
        except Exception:
            data['outbound']['ecs_external_calls'] = 0

        # By mode
        for mode in ['fast', 'deep', 'stream', 'multi-agent']:
            try:
                r = cw.get_metric_statistics(
                    Namespace='AlexAI', MetricName='ResearchQuery',
                    Dimensions=[
                        {'Name': 'Service', 'Value': 'alex-researcher'},
                        {'Name': 'Mode',    'Value': mode}
                    ],
                    StartTime=start, EndTime=end,
                    Period=3600 * hours, Statistics=['Sum']
                )
                count = int(sum(d['Sum'] for d in r['Datapoints']))
                if count > 0:
                    data['inbound'][f'research_{mode}'] = count
            except Exception:
                pass

        emit_metric('ALBTotalRequests',    data['alb'].get('total_requests', 0))
        emit_metric('ALB4xxErrors',        data['alb'].get('HTTPCode_ELB_4XX_Count', 0))
        emit_metric('ALB5xxErrors',        data['alb'].get('HTTPCode_ELB_5XX_Count', 0))
        emit_metric('OutboundAPICallsECS', data['outbound'].get('ecs_external_calls', 0))

        return data
    except Exception as e:
        print(f"API metrics error: {e}")
        return {}


# ============================================
# Rate Limit Forecasting
# ============================================
def forecast_rate_limits():
    try:
        BEDROCK_RPM = 100
        end = datetime.now(UTC)

        r = cw.get_metric_statistics(
            Namespace='AlexAI', MetricName='ResearchQuery',
            Dimensions=[{'Name': 'Service', 'Value': 'alex-researcher'}],
            StartTime=end - timedelta(hours=1), EndTime=end,
            Period=60, Statistics=['Sum']
        )

        recent_rpm    = [dp['Sum'] for dp in r['Datapoints']]
        avg_rpm       = sum(recent_rpm) / max(len(recent_rpm), 1) if recent_rpm else 0
        peak_rpm      = max(recent_rpm) if recent_rpm else 0
        capacity_used = (avg_rpm / BEDROCK_RPM) * 100
        peak_capacity = (peak_rpm / BEDROCK_RPM) * 100

        forecasts = []
        if capacity_used > 50:
            forecasts.append({
                "service": "Bedrock Nova Pro",
                "current": f"{avg_rpm:.1f} RPM",
                "limit":   f"{BEDROCK_RPM} RPM",
                "used":    f"{capacity_used:.1f}%",
                "risk":    "HIGH" if capacity_used > 80 else "MEDIUM",
                "action":  "Request quota increase" if capacity_used > 80 else "Monitor"
            })

        if peak_capacity > 70:
            forecasts.append({
                "service": "Bedrock (peak)",
                "current": f"{peak_rpm:.1f} RPM",
                "limit":   f"{BEDROCK_RPM} RPM",
                "used":    f"{peak_capacity:.1f}%",
                "risk":    "HIGH",
                "action":  "Enable provisioned throughput"
            })

        try:
            lc         = lambda_c.get_account_settings()
            total      = lc['AccountLimit']['ConcurrentExecutions']
            unreserved = lc['AccountLimit']['UnreservedConcurrentExecutions']
            used_pct   = ((total - unreserved) / total) * 100
            if used_pct > 50:
                forecasts.append({
                    "service": "Lambda Concurrency",
                    "current": f"{total - unreserved} used",
                    "limit":   f"{total} total",
                    "used":    f"{used_pct:.1f}%",
                    "risk":    "MEDIUM",
                    "action":  "Review concurrency settings"
                })
        except Exception:
            pass

        recs = []
        if capacity_used > 80:
            recs.append("URGENT: Request Bedrock quota via AWS Support")
        if capacity_used > 50:
            recs.append("Implement request queuing to smooth traffic")
        if not forecasts:
            recs.append("Rate limits healthy")

        emit_metric('BedrockCapacityUsed', capacity_used, 'Percent')
        emit_metric('BedrockPeakRPM',      peak_rpm)
        emit_metric('RateLimitRiskCount',  len([f for f in forecasts if f['risk'] == 'HIGH']))

        return {
            "avg_rpm":         round(avg_rpm, 2),
            "peak_rpm":        round(peak_rpm, 2),
            "capacity_used":   round(capacity_used, 1),
            "forecasts":       forecasts,
            "recommendations": recs
        }
    except Exception as e:
        print(f"Rate limit forecast error: {e}")
        return {"forecasts": [], "recommendations": ["Unable to forecast"]}


# ============================================
# Health Checks
# ============================================
def check_ecs():
    try:
        r       = ecs_c.describe_services(
            cluster=RESOURCES['ecs']['cluster'],
            services=[RESOURCES['ecs']['service']]
        )
        svc     = r['services'][0]
        running = svc['runningCount']
        desired = svc['desiredCount']
        status  = "healthy" if running == desired and running > 0 else \
                  "degraded" if running > 0 else "down"
        emit_metric('ECSRunningTasks', running)
        return {"service": "ECS Researcher", "status": status,
                "detail": f"{running}/{desired} tasks", "running": running}
    except Exception as e:
        return {"service": "ECS Researcher", "status": "error", "detail": str(e)[:100]}


def check_sagemaker():
    try:
        r      = sage_c.describe_endpoint(EndpointName=RESOURCES['sagemaker']['endpoint'])
        status = r['EndpointStatus']
        ok     = status == 'InService'
        emit_metric('SageMakerHealthy', 1 if ok else 0)
        return {"service": "SageMaker Embedding",
                "status": "healthy" if ok else "down", "detail": status}
    except Exception as e:
        return {"service": "SageMaker Embedding", "status": "error", "detail": str(e)[:100]}


def check_frontend():
    try:
        req  = urllib.request.Request(FRONTEND_URL)
        resp = urllib.request.urlopen(req, timeout=10)
        code = resp.getcode()
        emit_metric('FrontendHealthy', 1 if code == 200 else 0)
        return {"service": "Frontend (Vercel)",
                "status": "healthy" if code == 200 else "down",
                "detail": f"HTTP {code}"}
    except Exception as e:
        emit_metric('FrontendHealthy', 0)
        return {"service": "Frontend (Vercel)", "status": "down", "detail": str(e)[:100]}


def check_alb():
    if not ALB_URL:
        return {"service": "ECS API", "status": "unknown", "detail": "ALB_URL not set"}
    try:
        req  = urllib.request.Request(f"{ALB_URL}/health")
        resp = urllib.request.urlopen(req, timeout=10)
        body = json.loads(resp.read())
        ok   = body.get('status') == 'healthy'
        emit_metric('ALBHealthy', 1 if ok else 0)
        return {"service": "ECS API (ALB)",
                "status": "healthy" if ok else "degraded",
                "detail": body.get('status', 'unknown')}
    except Exception as e:
        emit_metric('ALBHealthy', 0)
        return {"service": "ECS API (ALB)", "status": "down", "detail": str(e)[:100]}


def check_aurora():
    try:
        rds_data.execute_statement(
            resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN,
            database=DB_NAME, sql="SELECT 1"
        )
        emit_metric('AuroraHealthy', 1)
        return {"service": "Aurora DB", "status": "healthy", "detail": "Connected"}
    except Exception as e:
        emit_metric('AuroraHealthy', 0)
        err = str(e)
        return {"service": "Aurora DB",
                "status": "degraded" if 'resuming' in err.lower() else "error",
                "detail": "Cold start" if 'resuming' in err.lower() else err[:100]}


def check_sqs():
    issues = []
    try:
        for name in ['alex-research-queue', 'alex-results-queue', 'alex-frontend-results']:
            url = f"https://sqs.{REGION}.amazonaws.com/{ACCOUNT_ID}/{name}"
            try:
                r    = sqs_c.get_queue_attributes(QueueUrl=url, AttributeNames=['All'])
                msgs = int(r['Attributes']['ApproximateNumberOfMessages'])
                nviz = int(r['Attributes']['ApproximateNumberOfMessagesNotVisible'])
                emit_metric('SQSMessageCount', msgs, dimensions={'Queue': name})
                if msgs > 100:
                    issues.append(f"{name}: {msgs} stuck messages")
                if nviz > 50:
                    issues.append(f"{name}: {nviz} in-flight messages")
            except Exception:
                pass
        return {"service": "SQS Queues",
                "status": "degraded" if issues else "healthy",
                "detail": ", ".join(issues) if issues else "All queues healthy"}
    except Exception as e:
        return {"service": "SQS Queues", "status": "error", "detail": str(e)[:100]}


def check_lambdas():
    errors = []
    try:
        for name in list(RESOURCES['lambdas'].keys())[:5]:
            try:
                r = cw.get_metric_statistics(
                    Namespace='AWS/Lambda', MetricName='Errors',
                    Dimensions=[{'Name': 'FunctionName', 'Value': name}],
                    StartTime=datetime.now(UTC) - timedelta(hours=1),
                    EndTime=datetime.now(UTC),
                    Period=3600, Statistics=['Sum']
                )
                if r['Datapoints'] and r['Datapoints'][0]['Sum'] > 5:
                    errors.append(f"{name}: {int(r['Datapoints'][0]['Sum'])} errors/hr")
            except Exception:
                pass
        return {"service": "Lambda Functions",
                "status": "degraded" if errors else "healthy",
                "detail": ", ".join(errors) if errors else "All healthy"}
    except Exception as e:
        return {"service": "Lambda Functions", "status": "error", "detail": str(e)[:100]}


def run_health_checks():
    checks = [
        check_ecs(), check_sagemaker(), check_alb(),
        check_frontend(), check_sqs(), check_lambdas(), check_aurora()
    ]
    healthy = len([c for c in checks if c['status'] == 'healthy'])
    emit_metric('HealthyServices', healthy)
    emit_metric('TotalServices',   len(checks))
    emit_metric('OverallHealth',   (healthy / len(checks)) * 100, 'Percent')
    for c in checks:
        print(f"  {c['service']}: {c['status']} — {c['detail']}")
    return checks


# ============================================
# Cost Monitoring
# ============================================
def get_daily_cost():
    try:
        today    = datetime.now(UTC).strftime('%Y-%m-%d')
        tomorrow = (datetime.now(UTC) + timedelta(days=1)).strftime('%Y-%m-%d')
        r = ce.get_cost_and_usage(
            TimePeriod={'Start': today, 'End': tomorrow},
            Granularity='DAILY', Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )
        services = {}
        total    = 0.0
        for result in r['ResultsByTime']:
            for group in result['Groups']:
                svc    = group['Keys'][0]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                if amount > 0.001:
                    services[svc] = round(amount, 4)
                    total += amount
        emit_metric('DailyCostTotal', total, 'None')
        for svc, amt in services.items():
            clean = svc.replace('Amazon ', '').replace('AWS ', '')[:20]
            emit_metric('ServiceCost', amt, 'None', {'Service': clean})
        return {'total': round(total, 4), 'services': services, 'date': today}
    except Exception as e:
        return {'total': 0, 'services': {}, 'date': '', 'error': str(e)}


# ============================================
# Start/Stop with Approval
# ============================================
def request_approval(action, reason):
    import uuid
    token = str(uuid.uuid4())[:8].upper()
    try:
        ssm.put_parameter(Name='/alex/ops/pending-token',
                          Value=token, Type='String', Overwrite=True)
        ssm.put_parameter(Name='/alex/ops/pending-action',
                          Value=action, Type='String', Overwrite=True)
    except Exception as e:
        print(f"SSM error: {e}")

    body = f"""Alex Ops Agent — Action Required
{'='*40}
ACTION: {action.upper()}
REASON: {reason}
TOKEN:  {token}

APPROVE: {FRONTEND_URL}/ops/appve?token={token}&action=approve
DENY:    {FRONTEND_URL}/ops/approve?token={token}&action=deny

Expires in 2 hours. No action = no change.
— Alex Ops Agent"""

    try:
        ses.send_email(
            Source=FROM_EMAIL,
            Destination={'ToAddresses': [ALERT_EMAIL]},
            Message={
                'Subject': {'Data': f'Alex Ops: Approval needed — {action}'},
                'Body':    {'Text': {'Data': body}}
            }
        )
        print(f"Approval sent — token: {token}")
    except Exception as e:
        print(f"SES error: {e}")
    return token


def start_services():
    try:
        ecs_c.update_service(
            cluster=RESOURCES['ecs']['cluster'],
            service=RESOURCES['ecs']['service'],
            desiredCount=1
        )
        print("ECS started")
        emit_metric('ServiceAction', 1, dimensions={'Action': 'start'})
    except Exception as e:
        print(f"ECS start error: {e}")


def stop_services():
    try:
        ecs_c.update_service(
        uster=RESOURCES['ecs']['cluster'],
            service=RESOURCES['ecs']['service'],
            desiredCount=0
        )
        print("ECS stopped")
        emit_metric('ServiceAction', 1, dimensions={'Action': 'stop'})
    except Exception as e:
        print(f"ECS stop error: {e}")


# ============================================
# AI Ops Digest (with traces + API costs)
# ============================================
def generate_digest(health_checks, costs, llm_metrics,
                    api_metrics, rate_limits, traces,
                    api_costs, issues):
    try:
        healthy    = len([c for c in health_checks if c['status'] == 'healthy'])
        score      = int((healthy / len(health_checks)) * 100)
        health_str = "\n".join([f"  {c['service']}: {c['status']} — {c['detail']}"
                                for c in health_checks])
        top_costs  = sorted(costs.get('services', {}).items(),
                            key=lambda x: x[1], reverse=True)[:5]
        cost_str   = "\n".join([f"  {s}: ${a}" for s, a in top_costs])
        rate_str   = "\n".join([
            f"  {f['service']}: {f['used']} [{f['risk']}] — {f['action']}"
            for f in rate_limits.get('forecasts', [])
        ]) or "  All within limits"

        # Tool call summary
        tool_str = "\n".join([
            f"  {tool}: {count} calls"
            for tool, count in (traces.get('most_used_tools') or [])[:5]
        ]) or "  No tool data"

        # API cost summary
        api_cost_str = "\n".join([
            f"  {api}: {info.get('calls', 0)} calls = ${info.get('cost', 0):.4f}"
            for api, info in api_costs.get('breakdown', {}).items()
        ]) or "  No API cost data"

        prompt = f"""You are Alex Ops, production AIOps agent for an AWS AI financial advisor.

PLATFORM HEALTH: {score}/100
{health_str}

COST TODAY: ${costs.get('total', 0):.4f} (threshold: ${COST_THRESHOLD})
{cost_str}

LLM OBSERVABILITY (24h):
  Queries:          {llm_metrics.get('TotalQueries', 0)}
  Avg latency:      {m_metrics.get('AvgLatency', 0)}s
  Error rate:       {llm_metrics.get('ErrorRate', 0)}%
  Cost per query:   ${llm_metrics.get('CostPerQuery', 0):.4f}
  Est tokens in:    {llm_metrics.get('EstimatedTokensIn', 0):,}
  Est tokens out:   {llm_metrics.get('EstimatedTokensOut', 0):,}
  Est LLM cost:     ${llm_metrics.get('EstimatedLLMCost', 0):.4f}
  Guardrail blocks: {llm_metrics.get('GuardrailBlocks', 0)}
  Fast latency:     {llm_metrics.get('fast_latency', 0)}s
  Deep latency:     {llm_metrics.get('deep_latency', 0)}s

AGENT TRACES (24h):
  Agent runs:       {traces.get('agent_runs', 0)}
  Planner runs:     {traces.get('planner_runs', 0)}
  Reporter runs:    {traces.get('reporter_runs', 0)}
  Total tool calls: {traces.get('total_tool_calls', 0)}
  Avg tasks/plan:   {traces.get('avg_tasks_per_plan', 0)}
Top tools:
{tool_str}

EXTERNAL API COSTS (24h):
  Total AWS API:    ${api_costs.get('total_aws_cost', 0):.4f}
  Total external:   ${api_costs.get('total_external_cost', 0):.6f}
  Grand total:      ${api_costs.get('grand_total', 0):.4f}
{api_cost_str}

API TRAFFIC:
  ALB requests:   {api_metrics.get('alb', {}).get('total_requests', 0)}
  4xx errors:     {api_metrics.get('alb', {}).get('HTTPCode_ELB_4XX_Count', 0)}
  5xx errors:     {api_metrics.get('alb', {}).get('HTTPCode_ELB_5XX_Count', 0)}
  Outbound calls: {api_metrics.get('outbound', {}).get('ecs_external_calls', 0)}
  By mode:        {json.dumps(api_metrics.get('inbound', {}))}

RATE LIMITS:
{rate_str}

ISSUES: {len(issues)}
{chr(10).join(['  - ' + i for i in issues]) if issues else '  None'}

AUTONOMOUS: {AUTONOMOUS}

Generate technical ops digest (max 600 words):
1. Health score with explanation of each service status
2. LLM performance: latency by mode, error rates, token efficiency, cost per query
3. Agent trace analysis: which tools called most, planner efficiency, reporter success
4. API cost breakdown: Bedrock vs SageMaker vs external, cost optimization opportunities
5. API traffic: inbound patterns, outbound call efficiency, error rates
6. Rate limit risks and specific capacity recommendations
7. Top 3 priority actions for next 24 hours (with specific commands if applicable)
8. Predicted risks next 48 hours

Be highly specific with numbers. This is for a developer who built this system."""

        response = bedrock.invoke_model(
            modelId='us.amazon.nova-lite-v1:0',
            contentType='application/json', accept='application/json',
            body=json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": 800, "temperature": 0.3}
            })
        )
        result = json.loads(response['body'].read())
        return result['output']['message']['content'][0]['text']

    except Exception as e:
        print(f"Digest error: {e}")
        healthy = len([c for c in health_checks if c['status'] == 'healthy'])
        return (f"Ops Digest — {datetime.now(UTC).isoformat()}\n"
                f"Health: {healthy}/{len(health_checks)} | "
                f"Ct: ${costs.get('total', 0):.2f} | Issues: {len(issues)}")


# ============================================
# Store Snapshot
# ============================================
def store_snapshot(health_checks, costs, llm_metrics,
                   api_metrics, rate_limits, traces,
                   api_costs, digest):
    try:
        full_data = {
            "health":      {c['service']: c['status'] for c in health_checks},
            "costs":       costs,
            "llm_metrics": llm_metrics,
            "api_metrics": api_metrics,
            "rate_limits": rate_limits,
            "traces":      traces,
            "api_costs":   api_costs
        }
        rds_data.execute_statement(
            resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN, database=DB_NAME,
            sql="""INSERT INTO ops_snapshots
                     (snapshot_time, health_status, daily_cost, digest)
                   VALUES (:time, :status::jsonb, :cost, :digest)""",
            parameters=[
                {'name': 'time',   'value': {'stringValue': datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}, 'typeHint': 'TIMESTAMP'},
                {'name': 'status', 'value': {'stringValue': json.dumps(full_data)}},
                {'name': 'cost',   'value': {'doubleValue': costs.get('total', 0)}},
                {'name': 'digest', 'value': {'stringValue': digest[:3000]}}
            ]
        )
        print("Snapshot stored")
    except Exception as e:
        print(f"Store error: {e}")


def send_email(subject, body):
    if not ALERT_EMAIL or not FROM_EMAIL:
        return
    try:
        ses.send_email(
            Source=FROM_EMAIL,
            Destination={'ToAddresses': [ALERT_EMAIL]},
            Message={
                'Subject': {'Data': subject},
                'Body':    {'Text': {'Data': body}}
            }
        )
        print(f"Email sent: {subject[:60]}")
    except Exception as e:
        print(f"Email error: {e}")


# ============================================
# Main Handler
# ============================================
def lambda_handler(event, context):
    now    = datetime.now(UTC)
    action = event.get('action', 'monitor')
    source = event.get('source', 'eventbridge')

    print(f"Alex Ops — {now.isoformat()} | {source} | {action} | auto={AUTONOMOUS}")
    emit_metric('OpsAgentRun', 1, dimensions={'Source': source})

    # Explicit control actions
    if action == 'start':
        if AUTONOMOUS:
            start_services()
            return {"statusCode": 200, "body": "Started (autonomous)"}
        token = request_approval('start_services', 'Manual start requested')
        return {"statusCode": 200, "body": f"Approval sent — token: {token}"}

    if action == 'stop':
        if AUTONOMOUS:
            stop_services()
            return {"statusCode": 200, "body": "Stopped (autonomous)"}
        token = request_approval('stop_services', 'Manual stop requested')
        return {"statusCode": 200, "body": f"Approval sent — token: {token}"}

    # Full monitoring run
    print("--- Health checks ---")
    health_checks = run_health_checks()

    print("--- Costs ---")
    costs = get_daily_cost()

    print("--- LLM metrics ---")
    llm_metrics = get_llm_metrics(hours=24)

    print("--- API metrics ---")
    api_metrics = get_api_metrics(hours=24)

    print("--- Rate limits ---")
    rate_limits = forecast_rate_limits()

    print("--- Agent traces ---")
    traces = get_agent_traces(hours=24)

    print("--- External API costs ---")
    api_costs = get_external_api_costs(hours=24)

    # Detect issues
    issues = []
    for c in health_checks:
        if c['status'] in ['down', 'error']:
            issues.append(f"{c['service']} is {c['status'].upper()}: {c['detail']}")

    if costs['total'] >= COST_THRESHOLD:
        issues.append(f"Cost alert: ${costs['total']:.2f} >= ${COST_THRESHOLD}")

    for f in rate_limits.get('forecasts', []):
        if f['risk'] == 'HIGH':
            issues.append(f"Rate limit: {f['service']} at {f['used']}")

    if llm_metrics.get('ErrorRate', 0) > 10:
        issues.append(f"High LLM error rate: {llm_metrics['ErrorRate']:.1f}%")

    # Auto-remediation
    ecs_check = next((c for c in health_checks if 'ECS' in c['service']), None)
    if ecs_check and ecs_check['status'] == 'down':
        if AUTONOMOUS:
            print("AUTO: ECS down — starting")
            start_services()
            issues.append("ECS auto-started (autonomous)")
            emit_metric('AutoRemediation', 1, dimensions={'Action': 'start_ecs'})
        else:
            token = request_approval(
                'start_ecs',
                f"ECS DOWN. Cost: ${costs['total']:.2f}. Platform unavailable."
            )
            issues.append(f"ECS down — token: {token}")
            emit_metric('ApprovalRequested', 1, dimensions={'Action': 'start_ecs'})

    # Generate digest
    print("--- Digest ---")
    digest = generate_digest(
        health_checks, costs, llm_metrics, api_metrics,
        rate_limits, traces, api_costs, issues
    )

    store_snapshot(health_checks, costs, llm_metrics, api_metrics,
                   rate_limits, traces, api_costs, digest)

    # Email decisions
    is_weekly  = now.weekday() == 0 and now.hour == 8
    has_issues = len(issues) > 0

    if has_issues:
        subject = f"Alex Ops Alert — {len(issues)} issues — ${costs['total']:.2f}"
        body    = ("ISSUES:\n" + "\n".join(f"  - {i}" for i in issues) +
                   f"\n\n{'='*40}\n\n{digest}")
        send_email(subject, body)
        emit_metric('AlertsSent', 1)
    elif is_weekly:
        subject = f"Alex Weekly Ops — {now.strftime('%B %d, %Y')}"
        body    = (f"Weekly Report\n{'='*40}\n\n{digest}\n\n"
                   f"API Costs: ${api_costs.get('grand_total', 0):.4f}\n"
                   f"Tool calls: {traces.get('total_tool_calls', 0)}\n"
                   f"Mode: {'AUTONOMOUS' if AUTONOMOUS else 'APPROVAL REQUIRED'}")
        send_email(subject, body)
        emit_metric('WeeklyReportSent', 1)

    healthy = len([c for c in health_checks if c['status'] == 'healthy'])
    result  = {
        "timestamp":        now.isoformat(),
        "health_score":     int((healthy / len(health_checks)) * 100),
        "healthy":          healthy,
        "total_services":   len(health_checks),
        "issues":           issues,
        "daily_cost":       costs['total'],
        "llm_queries":      llm_metrics.get('TotalQueries', 0),
        "llm_error_rate":   llm_metrics.get('ErrorRate', 0),
        "total_tool_calls": traces.get('total_tool_calls', 0),
        "api_grand_total":  api_costs.get('grand_total', 0),
        "autonomous":       AUTONOMOUS,
        "digest_preview":   digest[:400]
    }

    print(f"Done — score:{result['health_score']}/100 issues:{len(issues)}")
    return {"statusCode": 200, "body": json.dumps(result)}
