"""
Open Source Agent - LLM agent using Ollama or OpenRouter for cost optimization reasoning.

This module provides:
- OpenSourceAgent class with generate_optimization_report() and run() methods
- Support for Ollama (local) and OpenRouter (cloud) LLM providers
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional

import requests


class OpenSourceAgent:
    """LLM agent for generating cost optimization reports using open-source models."""
    
    def __init__(
        self,
        llm_provider: str = "ollama",
        model: str = "llama3",
        ollama_base_url: str = "http://localhost:11434",
    ):
        """
        Initialize the agent.
        
        Args:
            llm_provider: "ollama" for local or "openrouter" for cloud
            model: Model name (e.g., "llama3", "mistral", "openrouter/meta-llama/llama-3-70b-instruct")
            ollama_base_url: Base URL for Ollama API
        """
        self.llm_provider = llm_provider or os.environ.get("LLM_PROVIDER", "ollama")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3")
        self.ollama_base_url = ollama_base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    
    def _call_llm(self, messages: list[dict]) -> str:
        """
        Call the LLM with the given messages.
        
        Args:
            messages: List of message dicts with "role" and "content"
        
        Returns:
            The generated response text
        """
        if self.llm_provider == "ollama":
            return self._call_ollama(messages)
        elif self.llm_provider == "openrouter":
            return self._call_openrouter(messages)
        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_provider}")
    
    def _call_ollama(self, messages: list[dict]) -> str:
        """Call Ollama API."""
        url = f"{self.ollama_base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Could not connect to Ollama at {self.ollama_base_url}. "
                "Make sure Ollama is running. Try: ollama serve"
            )
        except Exception as e:
            raise RuntimeError(f"Ollama API error: {e}")
    
    def _call_openrouter(self, messages: list[dict]) -> str:
        """Call OpenRouter API."""
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set")
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/cloud-optimizer-mcp",
            "X-Title": "Cloud Optimizer MCP",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            raise RuntimeError(f"OpenRouter API error: {e}")
    
    def generate_optimization_report(self, unified_report: dict) -> dict:
        """
        Generate a cost optimization report from a unified report.
        
        Args:
            unified_report: The unified report dict from schema.py
        
        Returns:
            Dict containing the optimization report
        """
        system_prompt = """You are an expert Cloud Cost Optimization AI. You receive a unified JSON report about a codebase's cloud service usage, observability metrics, and AWS costs. Your job is to produce a structured Cost Optimization Report.

Rules:
- Reason only from the data provided. Do not invent metrics.
- Every recommendation must reference a specific service from the report.
- Savings estimates must be based on actual costs in the report.
- Output ONLY valid JSON matching the schema below. No preamble, no markdown.
- If data is missing or unclear, note it but still provide best-effort analysis.

Output schema:
{
  "report_title": "Cloud Cost Optimization Report",
  "generated_at": "<ISO timestamp>",
  "executive_summary": "<3-5 sentence summary>",
  "total_analyzed_cost_usd": <float>,
  "total_potential_savings_usd": <float>,
  "recommendations": [
    {
      "id": "rec_<number>",
      "service": "<aws service name>",
      "category": "compute|storage|database|networking|messaging",
      "issue": "<what is wrong>",
      "evidence": {
        "current_cost_usd": <float>,
        "utilization_pct": <float or null>,
        "latency_p99_ms": <float or null>,
        "error_rate_pct": <float or null>
      },
      "recommended_action": "<specific action>",
      "alternative_service": "<aws service or null>",
      "estimated_monthly_savings_usd": <float>,
      "implementation_steps": ["<step 1>", "<step 2>", ...],
      "risk": "low|medium|high",
      "priority": "critical|high|medium|low",
      "reversible": true|false
    }
  ],
  "service_insights": [
    {
      "service": "<name>",
      "finding": "<one key finding>",
      "action_required": true|false
    }
  ],
  "cost_breakdown_analysis": "<paragraph analyzing cost structure>",
  "quick_wins": ["<action that saves money with < 1 day effort>", ...]
}"""
        
        user_message = f"Here is the unified cloud report:\n{json.dumps(unified_report, indent=2, default=str)}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        response_text = self._call_llm(messages)
        
        # Try to parse JSON from response
        try:
            # Look for JSON in the response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                report = json.loads(json_text)
                return report
            else:
                # Try parsing the whole response
                report = json.loads(response_text)
                return report
        except json.JSONDecodeError:
            return {
                "error": True,
                "raw_response": response_text,
                "message": "Failed to parse LLM response as JSON. Please try again.",
            }
    
    def run(
        self,
        repo_path: Optional[str] = None,
        time_range_hours: int = 720,
        output_dir: str = ".",
    ) -> dict:
        """
        Run the full optimization analysis pipeline.
        
        Args:
            repo_path: Path to repository to analyze (default: current directory)
            time_range_hours: Time range for metrics
            output_dir: Directory to save output files
        
        Returns:
            The generated optimization report
        """
        repo_path = repo_path or "."
        
        print("=" * 70)
        print("🚀 Cloud Cost Optimization Agent")
        print("=" * 70)
        print(f"\n📂 Analyzing repository: {repo_path}")
        print(f"⏰ Time range: {time_range_hours} hours")
        print(f"🤖 LLM Provider: {self.llm_provider} ({self.model})")
        
        # Step 1: Fetch unified report from MCP server
        print("\n📊 Fetching unified report...")
        try:
            mcp_url = os.environ.get("MCP_SERVER_URL", "http://localhost:8000")
            resp = requests.post(
                f"{mcp_url}/mcp/tools/get_unified_report",
                json={
                    "repo_path": repo_path,
                    "time_range_hours": time_range_hours,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                unified_report = resp.json()
                print("✅ Unified report fetched successfully")
            else:
                print(f"⚠️ MCP server returned {resp.status_code}, using mock data")
                unified_report = self._get_mock_unified_report()
        except Exception as e:
            print(f"⚠️ Could not connect to MCP server: {e}")
            print("Using mock unified report for demonstration")
            unified_report = self._get_mock_unified_report()
        
        # Step 2: Generate optimization report
        print("\n🧠 Generating optimization report...")
        report = self.generate_optimization_report(unified_report)
        
        if "error" in report:
            print(f"❌ Error generating report: {report.get('message', 'Unknown error')}")
            print(f"Raw response: {report.get('raw_response', '')[:500]}...")
            return report
        
        # Step 3: Save outputs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save recommendations.json (for Streamlit frontend)
        recommendations_path = os.path.join(output_dir, "recommendations.json")
        with open(recommendations_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n💾 Recommendations saved to: {recommendations_path}")
        
        # Save full report
        full_report_path = os.path.join(output_dir, "cost_optimization_report.json")
        with open(full_report_path, "w") as f:
            json.dump({
                "unified_report": unified_report,
                "optimization_report": report,
            }, f, indent=2, default=str)
        print(f"📋 Full report saved to: {full_report_path}")
        
        # Step 4: Print summary
        self._print_summary(report)
        
        return report
    
    def _print_summary(self, report: dict) -> None:
        """Print a readable summary of the optimization report."""
        print("\n" + "=" * 70)
        print("📊 COST OPTIMIZATION SUMMARY")
        print("=" * 70)
        
        print(f"\n📝 Report: {report.get('report_title', 'N/A')}")
        print(f"💰 Total Analyzed Cost: ${report.get('total_analyzed_cost_usd', 0):.2f}/month")
        print(f"💡 Potential Savings: ${report.get('total_potential_savings_usd', 0):.2f}/month")
        
        savings = report.get("total_potential_savings_usd", 0)
        total = report.get("total_analyzed_cost_usd", 1)
        if total > 0:
            pct = (savings / total) * 100
            print(f"📈 Savings Potential: {pct:.1f}%")
        
        recommendations = report.get("recommendations", [])
        print(f"\n🎯 Recommendations: {len(recommendations)}")
        for i, rec in enumerate(recommendations[:5], 1):
            service = rec.get("service", "N/A")
            action = rec.get("recommended_action", "N/A")[:60]
            savings = rec.get("estimated_monthly_savings_usd", 0)
            priority = rec.get("priority", "N/A")
            print(f"   {i}. [{priority.upper()}] {service}: {action}... (save ${savings:.2f}/mo)")
        
        quick_wins = report.get("quick_wins", [])
        if quick_wins:
            print(f"\n⚡ Quick Wins ({len(quick_wins)}):")
            for win in quick_wins[:3]:
                print(f"   • {win[:80]}")
        
        print("\n" + "=" * 70)
    
    def _get_mock_unified_report(self) -> dict:
        """Get a mock unified report for testing."""
        try:
            from .codebase_analyzer_v2 import get_mock_codebase_analysis
            from .observability_client import get_mock_metrics
            from .cost_aggregator_v2 import get_mock_costs
            from .aws_service_knowledge import get_service_info
            from .schema import build_unified_report
        except ImportError:
            from codebase_analyzer_v2 import get_mock_codebase_analysis
            from observability_client import get_mock_metrics
            from cost_aggregator_v2 import get_mock_costs
            from aws_service_knowledge import get_service_info
            from schema import build_unified_report
        
        codebase = get_mock_codebase_analysis()
        metrics = get_mock_metrics("s3")
        costs = get_mock_costs()
        
        aws_info = {}
        for service in costs.get("by_service", {}).keys():
            info = get_service_info(service)
            if "not_found" not in info:
                aws_info[service] = info
        
        return build_unified_report(codebase, metrics, costs, aws_info)


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cloud Cost Optimization Agent")
    parser.add_argument("--repo-path", default=".", help="Path to repository to analyze")
    parser.add_argument("--time-range", type=int, default=720, help="Time range in hours")
    parser.add_argument("--provider", default="ollama", choices=["ollama", "openrouter"], help="LLM provider")
    parser.add_argument("--model", default="llama3", help="Model name")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    
    args = parser.parse_args()
    
    agent = OpenSourceAgent(
        llm_provider=args.provider,
        model=args.model,
    )
    
    report = agent.run(
        repo_path=args.repo_path,
        time_range_hours=args.time_range,
        output_dir=args.output_dir,
    )
    
    if "error" not in report:
        print("\n✅ Optimization report generated successfully!")
        sys.exit(0)
    else:
        print("\n❌ Failed to generate optimization report.")
        sys.exit(1)


if __name__ == "__main__":
    main()