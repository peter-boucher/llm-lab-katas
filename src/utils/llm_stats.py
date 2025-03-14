"""
Utility for tracking and reporting LLM usage statistics.

This module provides functions for collecting, aggregating, and reporting
statistics about LLM API usage, including token counts, costs, and Azure OpenAI prompt caching.
"""

import json
import logging
import threading
from typing import Dict, List, Any, Optional
import tiktoken

class LLMStats:
    def __init__(self, model_name: str,
                 input_cost_per_1m: float = 2.5,
                 output_cost_per_1m: float = 10.0):
        """
        Initialize the LLM stats tracker.

        Args:
            model_name: The name of the LLM model
            input_cost_per_1m: Cost in USD per 1 million input tokens
            output_cost_per_1m: Cost in USD per 1 million output tokens
        """
        self.model_name = model_name
        self.input_cost_per_1m = input_cost_per_1m
        self.output_cost_per_1m = output_cost_per_1m
        self.stats = {}
        self._1m = 1000000
        self.lock = threading.Lock()  # Add a lock for thread safety

        # Azure OpenAI prompt caching tracking
        self.azure_cached_stats = {}

        try:
            self.tokenizer = tiktoken.encoding_for_model(model_name)
        except Exception as e:
            logging.warning(f"Could not load tokenizer for {model_name}: {e}")
            self.tokenizer = None

    def record_usage(self, item_id: str, response_usage: Any) -> Dict[str, Any]:
        """
        Record the token usage for a single API call.

        Args:
            item_id: Identifier for the processed item
            response_usage: Usage object from the API response

        Returns:
            Dict containing the usage statistics
        """
        with self.lock:
            # Extract token counts
            prompt_tokens = response_usage.prompt_tokens
            completion_tokens = response_usage.completion_tokens
            total_tokens = response_usage.total_tokens

            # Check for Azure OpenAI prompt caching
            azure_cached_tokens = 0
            # Try to access prompt_tokens_details if it exists
            if hasattr(response_usage, 'prompt_tokens_details'):
                if hasattr(response_usage.prompt_tokens_details, 'cached_tokens'):
                    azure_cached_tokens = response_usage.prompt_tokens_details.cached_tokens

            # Calculate costs
            prompt_cost = (prompt_tokens / self._1m) * self.input_cost_per_1m
            completion_cost = (completion_tokens / self._1m) * self.output_cost_per_1m
            total_cost = prompt_cost + completion_cost

            # Calculate Azure cached cost savings (if any)
            azure_cached_cost_saved = 0
            if azure_cached_tokens > 0:
                # Azure charges 50% for cached tokens
                azure_cached_cost_saved = (azure_cached_tokens / self._1m) * (self.input_cost_per_1m * 0.5)

                # Record Azure caching stats
                self.azure_cached_stats[item_id] = {
                    "cached_tokens": azure_cached_tokens,
                    "cached_percentage": (azure_cached_tokens / prompt_tokens) * 100 if prompt_tokens > 0 else 0,
                    "cost_saved": azure_cached_cost_saved
                }

                # Log when we get cached tokens
                logging.info(f"Azure cached tokens: {azure_cached_tokens} for {item_id} (saved ~${azure_cached_cost_saved:.6f})")

            # Create usage report
            usage_report = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "prompt_cost_usd": prompt_cost,
                "completion_cost_usd": completion_cost,
                "total_cost_usd": total_cost,
                "azure_cached_tokens": azure_cached_tokens,
                "azure_cached_cost_saved": azure_cached_cost_saved
            }

            # Store the report
            self.stats[item_id] = usage_report

            # Log the usage
            logging.debug(f"Recorded usage for {item_id}: {total_tokens} tokens, ${total_cost:.6f}")

            return usage_report

    def get_token_count(self, text: str) -> Optional[int]:
        """Get the number of tokens in the text."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        return None

    def merge_stats(self) -> Dict[str, Any]:
        """
        Aggregate all recorded stats and generate a summary.

        Returns:
            Dict containing summary statistics and per-item details
        """
        # Make thread-safe copies of the data we need
        with self.lock:
            stats_copy = self.stats.copy() if self.stats else {}
            azure_cached_copy = self.azure_cached_stats.copy() if self.azure_cached_stats else {}

        # Process the copied data outside the lock
        if not stats_copy:
            return {
                "summary": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "prompt_cost_usd": 0.0,
                    "completion_cost_usd": 0.0,
                    "total_cost_usd": 0.0,
                    "items_processed": 0,
                    "azure_cached_items": 0,
                    "azure_cached_tokens": 0,
                    "azure_cached_cost_saved": 0.0
                },
                "details": {},
                "azure_cached": {}
            }

        # Calculate API call totals - no need to check if stats_copy is empty again
        prompt_tokens = sum(item["prompt_tokens"] for item in stats_copy.values())
        completion_tokens = sum(item["completion_tokens"] for item in stats_copy.values())
        total_tokens = sum(item["total_tokens"] for item in stats_copy.values())
        prompt_cost = sum(item["prompt_cost_usd"] for item in stats_copy.values())
        completion_cost = sum(item["completion_cost_usd"] for item in stats_copy.values())
        total_cost = sum(item["total_cost_usd"] for item in stats_copy.values())

        # Calculate Azure cached token totals
        azure_cached_tokens = 0
        azure_cached_cost_saved = 0.0
        if azure_cached_copy:
            azure_cached_tokens = sum(item["cached_tokens"] for item in azure_cached_copy.values())
            azure_cached_cost_saved = sum(item["cost_saved"] for item in azure_cached_copy.values())

        return {
            "summary": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "prompt_cost_usd": prompt_cost,
                "completion_cost_usd": completion_cost,
                "total_cost_usd": total_cost,
                "items_processed": len(stats_copy),
                "azure_cached_items": len(azure_cached_copy),
                "azure_cached_tokens": azure_cached_tokens,
                "azure_cached_cost_saved": azure_cached_cost_saved
            },
            "details": stats_copy,
            "azure_cached": azure_cached_copy
        }

    def save_report(self, output_path: str) -> None:
        """
        Save the usage report to a JSON file.

        Args:
            output_path: Path where to save the report
        """
        # Get merged stats without nested lock acquisition
        report = self.merge_stats()

        # Add model information
        report["model"] = self.model_name
        report["pricing"] = {
            "input_cost_per_1m_tokens": self.input_cost_per_1m,
            "output_cost_per_1m_tokens": self.output_cost_per_1m
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        logging.info(f"Saved usage report to {output_path}")

        # Log summary
        self.log_summary()

    def log_summary(self) -> None:
        """Log a summary of the usage statistics."""
        # Get the report without holding the lock during logging
        report = self.merge_stats()
        summary = report["summary"]

        logging.info("="*50)
        logging.info(f"LLM USAGE REPORT: {self.model_name}")
        logging.info("="*50)
        logging.info(f"Items processed: {summary['items_processed']}")
        logging.info(f"Total tokens: {summary['total_tokens']:,}")
        logging.info(f"  - Prompt tokens: {summary['prompt_tokens']:,}")
        logging.info(f"  - Completion tokens: {summary['completion_tokens']:,}")
        logging.info(f"Total cost: ${summary['total_cost_usd']:.4f}")
        logging.info(f"  - Prompt cost: ${summary['prompt_cost_usd']:.4f}")
        logging.info(f"  - Completion cost: ${summary['completion_cost_usd']:.4f}")

        # Add Azure caching information
        if summary['azure_cached_tokens'] > 0:
            logging.info("-"*50)
            logging.info(f"AZURE OPENAI PROMPT CACHING:")
            logging.info(f"  Items with cached tokens: {summary['azure_cached_items']}")
            logging.info(f"  Azure cached tokens: {summary['azure_cached_tokens']:,}")
            logging.info(f"  Cost saved (50% discount): ${summary['azure_cached_cost_saved']:.4f}")
            if summary['prompt_tokens'] > 0:
                cache_rate = (summary['azure_cached_tokens'] / summary['prompt_tokens']) * 100
                logging.info(f"  Caching rate: {cache_rate:.2f}% of prompt tokens")
        else:
            logging.info("-"*50)
            logging.info(f"No Azure OpenAI prompt caching detected")
            logging.info(f"To optimize for caching, keep system prompts consistent and at least 1024 tokens long")

        logging.info("="*50)