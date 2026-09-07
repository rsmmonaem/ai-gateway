from typing import List, Optional
from app.models.model_registry import ModelDefinition, ModelInstance


class LoadBalancer:
    """Dispatches requests among instances of a model using a health-aware, least-busy strategy."""

    @staticmethod
    def select_instance(model: ModelDefinition) -> Optional[ModelInstance]:
        if not model.instances:
            return None

        # Filter to enabled instances
        enabled_instances = [i for i in model.instances if i.enabled]
        if not enabled_instances:
            return None

        # Filter to healthy/online instances
        healthy_instances = [i for i in enabled_instances if i.health_status != "OFFLINE"]
        candidates = healthy_instances if healthy_instances else enabled_instances

        # Least-busy selection
        best = min(candidates, key=lambda inst: inst.active_requests)
        return best


load_balancer = LoadBalancer()
