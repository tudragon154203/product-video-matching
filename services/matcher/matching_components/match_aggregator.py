import numpy as np
from typing import Dict, Any, Optional, List
from common_py.logging_config import configure_logging

logger = configure_logging("matcher")

class MatchAggregator:
    def __init__(self, match_best_min: float, match_cons_min: int, match_accept: float):
        self.match_best_min = match_best_min
        self.match_cons_min = match_cons_min
        self.match_accept = match_accept

    async def aggregate_matches(self, best_matches: List[Dict[str, Any]], product_id: str, video_id: str) -> Optional[Dict[str, Any]]:
        """Aggregate pair matches to product-video level"""
        try:
            if not best_matches:
                return None
            
            best_matches.sort(key=lambda x: x["pair_score"], reverse=True)
            best_match = best_matches[0]
            best_score = best_match["pair_score"]
            consistency = sum(1 for match in best_matches if match["pair_score"] >= 0.80)
            
            if not self._apply_acceptance_rules(best_score, consistency, product_id, video_id):
                return None
            
            final_score = self._calculate_final_score(best_score, consistency, best_matches)
            
            if not self._check_final_acceptance_threshold(final_score, product_id, video_id):
                return None
            
            return {
                "best_img_id": best_match["img_id"],
                "best_frame_id": best_match["frame_id"],
                "ts": best_match["ts"],
                "score": min(1.0, final_score),
                "best_pair_score": best_score,
                "consistency": consistency,
                "total_pairs": len(best_matches)
            }
            
        except Exception as e:
            logger.error("Failed to aggregate matches", error=str(e))
            return None

    def _apply_acceptance_rules(self, best_score: float, consistency: int, product_id: str, video_id: str) -> bool:
        accept = False
        if best_score >= self.match_best_min and consistency >= self.match_cons_min:
            accept = True
        elif best_score >= 0.92:
            accept = True
        
        if not accept:
            logger.info("Match rejected by acceptance rules", 
                       product_id=product_id, 
                       video_id=video_id,
                       best_score=best_score,
                       consistency=consistency)
        return accept

    def _calculate_final_score(self, best_score: float, consistency: int, best_matches: List[Dict[str, Any]]) -> float:
        final_score = best_score
        if consistency >= 3:
            final_score += 0.02
        if len(set(match["img_id"] for match in best_matches)) >= 2:
            final_score += 0.02
        return final_score

    def _check_final_acceptance_threshold(self, final_score: float, product_id: str, video_id: str) -> bool:
        if final_score < self.match_accept:
            logger.info("Match rejected by final threshold", 
                       product_id=product_id, 
                       video_id=video_id,
                       final_score=final_score)
            return False
        return True
