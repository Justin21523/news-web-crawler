"""
Resource Manager — RAM monitoring, GPU detection, thread pool configuration.

Provides safe resource allocation for CPU/GPU workloads:
  - RAM-aware batch sizing
  - GPU detection (CUDA availability)
  - Thread pool sizing (up to 32 threads, RAM-safe)
  - Memory monitoring during batch processing

Usage:
    from utils.resource_manager import ResourceManager

    rm = ResourceManager(max_ram_gb=4.0)
    batch_size = rm.estimate_batch_size(texts, chars_per_item=5000)
    executor = rm.get_thread_pool()
    device = rm.get_device()  # 'cuda' or 'cpu'
"""

from __future__ import annotations

import logging
import os
import psutil
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

logger = logging.getLogger(__name__)

# Safety thresholds
DEFAULT_MAX_RAM_GB = 4.0          # Max RAM to use for processing
DEFAULT_RAM_SAFETY_MARGIN = 0.8   # Only use 80% of available RAM
DEFAULT_MAX_THREADS = 32
CHARS_PER_TOKEN_ESTIMATE = 1.5    # Chinese chars → tokens estimate


class ResourceManager:
    """Manages CPU/GPU/thread/RAM resources for pipeline operations."""

    def __init__(
        self,
        max_ram_gb: float = DEFAULT_MAX_RAM_GB,
        max_threads: int = DEFAULT_MAX_THREADS,
        safety_margin: float = DEFAULT_RAM_SAFETY_MARGIN,
    ):
        self.max_ram_bytes = int(max_ram_gb * 1024 ** 3)
        self.max_ram_bytes = int(self.max_ram_bytes * safety_margin)
        self.max_threads = min(max_threads, os.cpu_count() or 32)
        self._gpu_available: Optional[bool] = None

    # ------------------------------------------------------------------
    # GPU
    # ------------------------------------------------------------------
    def gpu_available(self) -> bool:
        """Check if CUDA GPU is available."""
        if self._gpu_available is not None:
            return self._gpu_available

        try:
            import torch
            self._gpu_available = torch.cuda.is_available()
            if self._gpu_available:
                logger.info(f"GPU available: {torch.cuda.get_device_name(0)} "
                           f"({torch.cuda.device_count()} device(s))")
        except ImportError:
            self._gpu_available = False
        return self._gpu_available

    def get_device(self) -> str:
        return "cuda" if self.gpu_available() else "cpu"

    def get_cuda_device_id(self) -> int:
        """Return device_id for CKIP/torch (-1 = CPU, 0+ = GPU)."""
        return 0 if self.gpu_available() else -1

    # ------------------------------------------------------------------
    # RAM
    # ------------------------------------------------------------------
    def current_ram_usage_gb(self) -> float:
        """Current process RAM usage in GB."""
        proc = psutil.Process(os.getpid())
        return proc.memory_info().rss / (1024 ** 3)

    def available_ram_gb(self) -> float:
        """Available system RAM in GB."""
        return psutil.virtual_memory().available / (1024 ** 3)

    def is_ram_safe(self, additional_gb: float = 0.5) -> bool:
        """Check if loading additional_gb is within safe limits."""
        available = self.available_ram_gb()
        return available >= additional_gb and self.current_ram_usage_gb() + additional_gb <= self.max_ram_bytes / (1024 ** 3)

    def estimate_batch_size(self, texts: list[str],
                            chars_per_item: int = 5000) -> int:
        """
        Estimate safe batch size based on RAM budget.

        Args:
            texts: List of texts (to gauge size).
            chars_per_item: Estimated chars per item.

        Returns:
            Safe batch size.
        """
        if not texts:
            return 64

        # Estimate tokens per item
        tokens_per_item = chars_per_item / CHARS_PER_TOKEN_ESTIMATE
        # Rough estimate: 1 token ≈ 4 bytes in memory (with overhead)
        bytes_per_item = int(tokens_per_item * 4 * 8)  # model overhead factor

        safe_bytes = min(self.max_ram_bytes, int(self.available_ram_gb() * 1024 ** 3 * 0.5))
        batch = max(8, min(256, safe_bytes // max(bytes_per_item, 1)))
        return batch

    def log_ram_status(self, label: str = ""):
        """Log current RAM status."""
        used = self.current_ram_usage_gb()
        avail = self.available_ram_gb()
        logger.info(f"[RAM{f' {label}' if label else ''}] "
                   f"Used: {used:.2f} GB | Available: {avail:.2f} GB | "
                   f"Budget: {self.max_ram_bytes / 1024**3:.2f} GB")

    # ------------------------------------------------------------------
    # Thread Pool
    # ------------------------------------------------------------------
    def get_thread_pool(self, max_workers: int | None = None) -> ThreadPoolExecutor:
        """Get a thread pool executor with safe thread count."""
        workers = min(max_workers or self.max_threads, self.max_threads)
        return ThreadPoolExecutor(max_workers=workers, thread_name_prefix="nlp_worker")

    # ------------------------------------------------------------------
    # Batch processing with RAM monitoring
    # ------------------------------------------------------------------
    def process_in_batches(self, items: list, processor,
                           batch_size: int | None = None,
                           desc: str = "Processing"):
        """
        Process items in batches with RAM monitoring.

        Args:
            items: List of items to process.
            processor: Callable that takes a batch (list) and returns results.
            batch_size: Override batch size (auto-estimated if None).
            desc: Description for logging.

        Returns:
            List of all results.
        """
        if not items:
            return []

        bs = batch_size or self.estimate_batch_size(
            items if isinstance(items[0], str) else [""] * len(items),
            chars_per_item=5000
        )

        self.log_ram_status(f"start {desc}")
        logger.info(f"Processing {len(items):,} items in batches of {bs} "
                   f"({(len(items) + bs - 1) // bs} batches)")

        results = []
        for i in range(0, len(items), bs):
            batch = items[i:i + bs]
            batch_results = processor(batch)
            results.extend(batch_results)

            # RAM check every 4 batches
            if (i // bs) % 4 == 0:
                self.log_ram_status(f"{desc} {i}/{len(items)}")

                # If RAM is running high, suggest smaller batches
                if not self.is_ram_safe(2.0):
                    logger.warning("RAM pressure detected — consider reducing batch_size")

        self.log_ram_status(f"done {desc}")
        return results
