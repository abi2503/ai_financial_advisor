resource "aws_sns_topic" "alex_alarms" {
  name = "alex-ai-alarms"
  tags = { Project = "alex" }
}

resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "alex-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ResearchError"
  namespace           = "AlexAI"
  period              = 300
  statistic           = "Sum"
  threshold           = 3
  alarm_description   = "Alex research error rate is high"
  alarm_actions       = [aws_sns_topic.alex_alarms.arn]
  dimensions          = { Service = "alex-researcher" }
  tags                = { Project = "alex" }
}

resource "aws_cloudwatch_metric_alarm" "high_latency" {
  alarm_name          = "alex-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "ResearchLatency"
  namespace           = "AlexAI"
  period              = 300
  statistic           = "Average"
  threshold           = 120
  alarm_description   = "Alex research latency is high"
  alarm_actions       = [aws_sns_topic.alex_alarms.arn]
  dimensions          = { Service = "alex-researcher", Mode = "fast" }
  tags                = { Project = "alex" }
}


resource "aws_cloudwatch_dashboard" "alex" {
  dashboard_name = "Alex-AI-Platform"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title       = "Research Queries Per Hour"
          view        = "timeSeries"
          stat        = "Sum"
          period      = 3600
          region      = "us-east-1"
          annotations = { horizontal = [] }
          metrics = [
            ["AlexAI", "ResearchQuery", "Mode", "fast", "Service", "alex-researcher", { label = "Fast Research" }],
            ["AlexAI", "ResearchQuery", "Mode", "deep", "Service", "alex-researcher", { label = "Deep Research" }]
          ]
          yAxis = { left = { min = 0 } }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title       = "Research Success Rate"
          view        = "timeSeries"
          stat        = "Average"
          period      = 3600
          region      = "us-east-1"
          annotations = { horizontal = [] }
          metrics = [
            ["AlexAI", "ResearchSuccess", "Mode", "fast", "Service", "alex-researcher", { label = "Fast Success" }],
            ["AlexAI", "ResearchSuccess", "Mode", "deep", "Service", "alex-researcher", { label = "Deep Success" }]
          ]
          yAxis = { left = { min = 0, max = 1 } }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Research Latency (seconds)"
          view   = "timeSeries"
          stat   = "Average"
          period = 300
          region = "us-east-1"
          metrics = [
            ["AlexAI", "ResearchLatency", "Mode", "fast", "Service", "alex-researcher", { label = "Fast Latency" }],
            ["AlexAI", "ResearchLatency", "Mode", "deep", "Service", "alex-researcher", { label = "Deep Latency" }]
          ]
          yAxis = { left = { min = 0 } }
          annotations = {
            horizontal = [
              { value = 60,  label = "Fast target",  color = "#ff9900" },
              { value = 300, label = "Deep target",  color = "#ff0000" }
            ]
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title       = "Research Errors"
          view        = "timeSeries"
          stat        = "Sum"
          period      = 300
          region      = "us-east-1"
          annotations = { horizontal = [] }
          metrics = [
            ["AlexAI", "ResearchError", "Mode", "fast", "Service", "alex-researcher", { label = "Fast Errors", color = "#ff0000" }],
            ["AlexAI", "ResearchError", "Mode", "deep", "Service", "alex-researcher", { label = "Deep Errors", color = "#ff6600" }]
          ]
          yAxis = { left = { min = 0 } }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          title       = "Autonomous Research Pipeline"
          view        = "timeSeries"
          stat        = "Sum"
          period      = 3600
          region      = "us-east-1"
          annotations = { horizontal = [] }
          metrics = [
            ["AlexAI", "AutoResearchTrigger", "Service", "alex-researcher", { label = "Scheduler Triggers" }],
            ["AlexAI", "AutoResearchSuccess",  "Service", "alex-researcher", { label = "Pipeline Success" }]
          ]
          yAxis = { left = { min = 0 } }
        }
      },
      {
        type   = "text"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          markdown = "## Alex AI Platform\n\n**Queries**: Total per hour by mode\n\n**Success Rate**: Target >95% fast, >90% deep\n\n**Latency**: Fast <60s | Deep <300s\n\n**Errors**: Investigate if >3 in 5 mins\n\n**Auto Pipeline**: Fires every 2 hours"
        }
      }
    ]
  })
}

# ============================================
# Bedrock Guardrail
# Why: Safety layer on every AI response
#      Financial advice requires protection
# ============================================

resource "aws_bedrock_guardrail" "alex" {
  name                      = "alex-financial-guardrail"
  description               = "Safety guardrail for Alex AI financial research"
  blocked_input_messaging   = "I can only help with financial research topics. Please ask about stocks, markets, or investment analysis."
  blocked_outputs_messaging = "This response was filtered for safety. Please rephrase your question about financial research."

  # Topic Policy
  # Why: Block requests outside financial research scope
  #      Prevents misuse of the platform
  topic_policy_config {
    topics_config {
      name       = "harmful-financial-advice"
      definition = "Specific investment advice guaranteeing returns or recommending putting all assets in one investment"
      examples   = [
        "Put all your savings in this stock",
        "This investment guarantees 100% returns",
        "You should mortgage your house to buy crypto"
      ]
      type = "DENY"
    }

    topics_config {
      name       = "off-topic-requests"
      definition = "Requests unrelated to financial research, stock analysis, or market information"
      examples   = [
        "Write me a poem",
        "Help me with my homework",
        "Tell me a joke"
      ]
      type = "DENY"
    }
  }

  # Content Policy
  # Why: Block harmful content categories
  sensitive_information_policy_config {
    pii_entities_config {
      type   = "SSN"
      action = "BLOCK"
    }
    pii_entities_config {
      type   = "CREDIT_DEBIT_CARD_NUMBER"
      action = "BLOCK"
    }
    pii_entities_config {
      type   = "BANK_ACCOUNT_NUMBER"
      action = "BLOCK"
    }
    pii_entities_config {
      type   = "EMAIL"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "PHONE"
      action = "ANONYMIZE"
    }
  }

  # Word Policy
  # Why: Block specific harmful phrases
  word_policy_config {
    words_config { text = "guaranteed returns" }
    words_config { text = "get rich quick" }
    words_config { text = "risk free investment" }
    words_config { text = "insider tip" }
    words_config { text = "pump and dump" }
  }

  tags = { Project = "alex" }
}

# Guardrail Version
# Why: Guardrails need a version to be usable
#      Version 1 = first published version
resource "aws_bedrock_guardrail_version" "alex" {
  guardrail_id = aws_bedrock_guardrail.alex.guardrail_id
  description  = "Version 1 — initial financial research guardrail"
}