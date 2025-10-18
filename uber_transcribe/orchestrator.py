import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any

from .models import SourceItem
from .sources.youtube import YouTubeSource
from .metadata_providers.audiodharma import AudioDharmaProvider

# A registry to map config types to their corresponding classes
DISCOVERY_SOURCE_REGISTRY = {
    "youtube_playlist": YouTubeSource,
}
METADATA_PROVIDER_REGISTRY = {
    "audiodharma": AudioDharmaProvider,
}

class Orchestrator:
    def __init__(self, config_path: Path):
        """
        Initializes the orchestrator, loading the configuration and instantiating
        the necessary sources and providers.
        """
        logging.info(f"Loading configuration from {config_path}...")
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.cache_root = Path("uber_transcribe/cache")
        
        self.discovery_sources = []
        for source_config in self.config.get("discovery_sources", []):
            source_type = source_config.get("type")
            if source_type in DISCOVERY_SOURCE_REGISTRY:
                SourceClass = DISCOVERY_SOURCE_REGISTRY[source_type]
                # Pass the specific config and the cache root to the source
                self.discovery_sources.append(SourceClass(source_config, self.cache_root / "youtube"))
                logging.info(f"Initialized discovery source: {source_type}")

        self.metadata_providers = []
        for provider_config in self.config.get("metadata_providers", []):
            provider_type = provider_config.get("type")
            if provider_type in METADATA_PROVIDER_REGISTRY:
                ProviderClass = METADATA_PROVIDER_REGISTRY[provider_type]
                # Pass the specific config and the cache root to the provider
                self.metadata_providers.append(ProviderClass(self.cache_root / "audiodharma"))
                logging.info(f"Initialized metadata provider: {provider_type}")

    def run_stage_1_update_metadata_caches(self):
        """
        (Workflow Stage 1)
        Updates the local caches for all configured metadata providers.
        """
        logging.info("\n--- Stage 1: Updating Metadata Caches ---")
        for provider in self.metadata_providers:
            provider.bulk_load_data()
        logging.info("--- Stage 1 Complete ---")

    def run_stage_2_discover_and_match(self) -> List[SourceItem]:
        """
        (Workflow Stage 2)
        Discovers all SourceItems, filters them, and enriches them with metadata.
        
        Returns:
            A list of enriched SourceItem objects.
        """
        logging.info("\n--- Stage 2: Discovering and Matching Source Items ---")
        
        # Discover
        all_items: Dict[str, SourceItem] = {}
        for source in self.discovery_sources:
            discovered_items = source.discover_items()
            for item in discovered_items:
                if item.source_id not in all_items:
                    all_items[item.source_id] = item
        
        logging.info(f"Discovered {len(all_items)} unique items.")

        # TODO: Filter by metadata_wait_days_delay

        # Match
        enriched_items = []
        for item in all_items.values():
            for provider in self.metadata_providers:
                metadata = provider.lookup(item)
                if metadata:
                    item.supplemental_metadata.update(metadata)
            enriched_items.append(item)
        
        logging.info(f"Finished matching for {len(enriched_items)} items.")
        logging.info("--- Stage 2 Complete ---")
        return enriched_items


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    config_file = Path("uber_transcribe/config.yaml")
    orchestrator = Orchestrator(config_path=config_file)
    
    orchestrator.run_stage_1_update_metadata_caches()
    
    final_items = orchestrator.run_stage_2_discover_and_match()

    if final_items:
        print(f"\n--- Enriched Data Samples ---")
        # Print a few items that have supplemental metadata
        found_samples = 0
        for item in final_items:
            if item.supplemental_metadata:
                print(f"\nSource ID: {item.source_id}")
                print(f"  Type: {item.source_type.value}")
                print(f"  Supplemental Metadata: {item.supplemental_metadata}")
                found_samples += 1
                if found_samples >= 5:
                    break
        if found_samples == 0:
            print("No items with supplemental metadata were found in this run.")

