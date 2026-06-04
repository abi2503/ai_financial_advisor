"""
MCP server configuration for web browsing
"""
import os
import glob
from agents.mcp import MCPServerStdio


def create_playwright_mcp_server(timeout_seconds: int = 120):
    """
    Create Playwright MCP server for web browsing.
    Uses pre-installed @playwright/mcp@0.0.74 at known path.
    """

    args = [
        "--headless",
        "--isolated",
        "--no-sandbox",
        "--ignore-https-errors",
        "--user-agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ]

    is_container = (
        os.path.exists("/.dockerenv") or
        bool(os.environ.get("AWS_EXECUTION_ENV")) or
        bool(os.environ.get("ECS_CONTAINER_METADATA_URI"))
    )

    if is_container:
        # Find Chrome dynamically
        chrome_paths = glob.glob(
            "/root/.cache/ms-playwright/chromium-*/chrome-linux*/chrome"
        )
        if chrome_paths:
            print(f"DEBUG: Found Chrome at: {chrome_paths[0]}")
            args.extend(["--executable-path", chrome_paths[0]])
        else:
            print("DEBUG: Chrome not found!")

        # Use pre-installed MCP at known path
        # Path confirmed via --no-cache Docker build
        cli_path = "/usr/local/lib/node_modules/@playwright/mcp/cli.js"

        if os.path.exists(cli_path):
            print(f"DEBUG: Using MCP CLI at: {cli_path}")
            params = {
                "command": "node",
                "args": [cli_path, *args]
            }
        else:
            # Fallback — dynamic search
            print(f"DEBUG: CLI not at expected path, searching...")
            import subprocess
            result = subprocess.run(
                ["find", "/usr/local/lib", "-name", "cli.js",
                 "-path", "*playwright/mcp/cli.js"],
                capture_output=True, text=True
            )
            found = result.stdout.strip().split("\n")[0]
            if found:
                print(f"DEBUG: Found via search: {found}")
                params = {"command": "node", "args": [found, *args]}
            else:
                print("DEBUG: Falling back to npx")
                params = {
                    "command": "npx",
                    "args": ["@playwright/mcp@0.0.74", *args]
                }
    else:
        # Local development
        params = {
            "command": "npx",
            "args": ["@playwright/mcp@0.0.74", *args]
        }

    print(f"DEBUG: MCP command: {params['command']} {params['args'][0]}")

    return MCPServerStdio(
        params=params,
        client_session_timeout_seconds=timeout_seconds
    )