import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CityMatcher:
    """Matches city names to destination IDs using deterministic or LLM fallback."""

    def __init__(self, agent, destination_map: Dict[str, int]):
        self.agent = agent
        self.destination_map = destination_map

    def match(self, city_name: str) -> Optional[int]:
        """Return destination code for a city."""
        city_key = city_name.lower()

        # Step 1: deterministic match
        if city_key in self.destination_map:
            return self.destination_map[city_key]

        # Step 2: LLM fallback
        logger.warning(f"No exact match for '{city_name}', trying LLM fallback...")
        return self._llm_fallback(city_name)

    def _llm_fallback(self, city_name: str) -> Optional[int]:
        prompt = f"""
You are a strict data matching system.
Input city: "{city_name}"
Available cities: {list(self.destination_map.keys())}
Return EXACT match (case-insensitive) or NONE.
Output ONLY the city name or NONE.
"""
        try:
            response = self.agent.chat(messages=[{"role": "user", "content": prompt}])
            match = response.strip().lower()
            if match == "none" or match not in self.destination_map:
                logger.error(f"LLM returned invalid match '{match}' for '{city_name}'")
                return None
            logger.info(f"LLM matched '{city_name}' → '{match}'")
            return self.destination_map[match]
        except Exception as e:
            logger.error(f"LLM matching failed for {city_name}: {e}")
            return None
