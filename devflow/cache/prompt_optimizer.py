"""
Prompt Optimizer - Token counting and prompt compression.

Optimizes prompts to reduce token usage and API costs.
"""

import re
import threading
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class PromptStats:
    """Statistics about a prompt."""
    original_tokens: int
    optimized_tokens: int
    compression_ratio: float
    optimizations_applied: List[str] = field(default_factory=list)


@dataclass
class OptimizerConfig:
    """Configuration for prompt optimization."""
    max_tokens: int = 200000
    enable_whitespace_removal: bool = True
    enable_duplicate_removal: bool = True
    enable_template_compression: bool = True
    preserve_code_blocks: bool = True
    preserve_structure: bool = True


class PromptOptimizer:
    """
    Optimizes prompts to reduce token usage.

    Responsibilities:
    - Token counting for accurate cost estimation
    - Prompt compression to reduce token usage
    - Redundancy removal
    - Template optimization
    - Statistics tracking

    Optimization Strategies:
    1. Whitespace normalization (removes excessive whitespace)
    2. Duplicate line removal
    3. Template compression (removes redundant boilerplate)
    4. Structure preservation (keeps code blocks intact)
    """

    def __init__(self, config: Optional[OptimizerConfig] = None):
        """
        Initialize the prompt optimizer.

        Args:
            config: Optional optimizer configuration
        """
        self.config = config or OptimizerConfig()
        self.lock = threading.Lock()
        self.stats = {
            "prompts_processed": 0,
            "total_original_tokens": 0,
            "total_optimized_tokens": 0,
            "total_tokens_saved": 0,
        }

        # Token approximation (rough estimate: ~4 chars per token)
        self.chars_per_token = 4

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using approximation.

        Note: This is a rough approximation. For accurate token counting,
        use tiktoken or the Anthropic API's token counting feature.

        Args:
            text: Text to count tokens in

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Approximate: ~4 characters per token for English text
        # This varies by language and content type
        return max(1, len(text) // self.chars_per_token)

    def optimize(self, prompt: str,
                preserve_code_blocks: Optional[bool] = None) -> Tuple[str, PromptStats]:
        """
        Optimize a prompt to reduce token usage.

        Args:
            prompt: The prompt to optimize
            preserve_code_blocks: Whether to preserve code blocks

        Returns:
            Tuple of (optimized_prompt, stats)
        """
        with self.lock:
            original_tokens = self.count_tokens(prompt)
            optimizations = []
            optimized = prompt

            # Apply whitespace optimization
            if self.config.enable_whitespace_removal:
                optimized = self._optimize_whitespace(optimized)
                if len(optimized) < len(prompt):
                    optimizations.append("whitespace_normalization")

            # Apply duplicate removal
            if self.config.enable_duplicate_removal:
                optimized = self._remove_duplicates(optimized)
                if len(optimized) < len(prompt):
                    optimizations.append("duplicate_removal")

            # Apply template compression
            if self.config.enable_template_compression:
                optimized = self._compress_templates(optimized)
                if len(optimized) < len(prompt):
                    optimizations.append("template_compression")

            # Calculate stats
            optimized_tokens = self.count_tokens(optimized)
            tokens_saved = original_tokens - optimized_tokens
            compression_ratio = tokens_saved / original_tokens if original_tokens > 0 else 0

            stats = PromptStats(
                original_tokens=original_tokens,
                optimized_tokens=optimized_tokens,
                compression_ratio=compression_ratio,
                optimizations_applied=optimizations,
            )

            # Update global stats
            self.stats["prompts_processed"] += 1
            self.stats["total_original_tokens"] += original_tokens
            self.stats["total_optimized_tokens"] += optimized_tokens
            self.stats["total_tokens_saved"] += tokens_saved

            return optimized, stats

    def _optimize_whitespace(self, text: str) -> str:
        """
        Optimize whitespace by removing excessive blank lines and spaces.

        Preserves code blocks if preserve_code_blocks is enabled.

        Args:
            text: Text to optimize

        Returns:
            Optimized text
        """
        if not self.config.preserve_code_blocks:
            # Simple whitespace optimization
            # Replace multiple spaces with single space
            text = re.sub(r' +', ' ', text)
            # Replace multiple newlines with max 2 newlines
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n\n', text)
            return text.strip()

        # Preserve code blocks
        lines = text.split('\n')
        in_code_block = False
        optimized_lines = []
        consecutive_blank = 0

        for line in lines:
            # Check for code block markers
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                optimized_lines.append(line)
                consecutive_blank = 0
                continue

            if in_code_block:
                # Preserve exact whitespace in code blocks
                optimized_lines.append(line)
                consecutive_blank = 0
            else:
                # Optimize non-code text
                stripped = line.strip()
                if not stripped:
                    consecutive_blank += 1
                    if consecutive_blank <= 2:  # Allow max 2 blank lines
                        optimized_lines.append(line)
                else:
                    consecutive_blank = 0
                    # Remove trailing spaces
                    optimized_lines.append(line.rstrip())

        return '\n'.join(optimized_lines)

    def _remove_duplicates(self, text: str) -> str:
        """
        Remove duplicate consecutive lines.

        Args:
            text: Text to deduplicate

        Returns:
            Text with duplicates removed
        """
        lines = text.split('\n')
        seen = set()
        unique_lines = []

        for line in lines:
            # Use stripped version for comparison but preserve original
            line_key = line.strip()
            if line_key and line_key in seen and not line.startswith(' '):
                # Skip duplicate (but not indented lines which might be code)
                continue
            seen.add(line_key)
            unique_lines.append(line)

        return '\n'.join(unique_lines)

    def _compress_templates(self, text: str) -> str:
        """
        Compress common template patterns.

        Removes redundant boilerplate like repeated instructions.

        Args:
            text: Text to compress

        Returns:
            Compressed text
        """
        # Remove repeated phrases
        patterns = [
            (r'Please +', 'Please '),
            (r'Make sure to +', 'Ensure '),
            (r'You should +', ''),
            (r'You need to +', ''),
            (r'You must +', ''),
        ]

        compressed = text
        for pattern, replacement in patterns:
            compressed = re.sub(pattern, replacement, compressed)

        return compressed

    def truncate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """
        Truncate a prompt to fit within max tokens.

        Attempts to truncate intelligently by preserving structure.

        Args:
            prompt: The prompt to truncate
            max_tokens: Maximum tokens (defaults to config.max_tokens)

        Returns:
            Truncated prompt
        """
        if max_tokens is None:
            max_tokens = self.config.max_tokens

        current_tokens = self.count_tokens(prompt)
        if current_tokens <= max_tokens:
            return prompt

        # Simple truncation: take first N characters
        # A smarter implementation would preserve sections
        max_chars = max_tokens * self.chars_per_token
        truncated = prompt[:max_chars]

        # Try to end at a newline
        last_newline = truncated.rfind('\n')
        if last_newline > max_chars * 0.9:  # If newline is close to end
            truncated = truncated[:last_newline]

        return truncated

    def get_stats(self) -> Dict[str, Any]:
        """
        Get optimizer statistics.

        Returns:
            Dictionary containing optimizer metrics
        """
        with self.lock:
            total_prompts = self.stats["prompts_processed"]
            total_original = self.stats["total_original_tokens"]
            total_optimized = self.stats["total_optimized_tokens"]

            avg_compression = 0
            if total_original > 0:
                avg_compression = (total_original - total_optimized) / total_original

            return {
                "prompts_processed": total_prompts,
                "total_original_tokens": total_original,
                "total_optimized_tokens": total_optimized,
                "total_tokens_saved": self.stats["total_tokens_saved"],
                "average_compression_ratio": avg_compression,
            }

    def reset_stats(self):
        """Reset optimizer statistics."""
        with self.lock:
            for key in self.stats:
                self.stats[key] = 0

    def batch_optimize(self, prompts: List[str]) -> List[Tuple[str, PromptStats]]:
        """
        Optimize multiple prompts.

        Args:
            prompts: List of prompts to optimize

        Returns:
            List of (optimized_prompt, stats) tuples
        """
        results = []
        for prompt in prompts:
            optimized, stats = self.optimize(prompt)
            results.append((optimized, stats))
        return results
