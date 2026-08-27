import asyncio

import pytest

from models.product import Product, ProductStatus, ProductType, Platform
from services.etsy_service import EtsyService
from services.pod_workflow import PODWorkflowBlocked, _canonical_hash, pod_workflow_service
from services.printify_service import PrintifyService


class _FakeQuery:
    def __init__(self, product):
        self.product = product

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.product


class _FakeDb:
    def __init__(self, product):
        self.product = product

    def query(self, model):
        return _FakeQuery(self.product)


def _product() -> Product:
    product = Product()
    product.id = 7
    product.platform = Platform.ETSY
    product.product_type = ProductType.T_SHIRT
    product.status = ProductStatus.DRAFT
    product.title = "Verified POD Shirt"
    product.description = "A production-ready physical POD product."
    product.price = 29.0
    product.tags = ["shirt", "pod"]
    product.printify_blueprint_id = None
    product.printify_variant_ids = []
    return product


def test_pod_input_hash_is_order_independent_and_stable():
    first = _canonical_hash({"b": [2, 3], "a": 1})
    second = _canonical_hash({"a": 1, "b": [2, 3]})
    assert first == second
    assert len(first) == 64


def test_etsy_physical_pod_configuration_fails_closed_without_profiles():
    service = EtsyService()
    service.api_key = "key"
    service.api_secret = "secret"
    service.access_token = "token"
    service.shop_id = "123"
    service.shipping_profile_id = 0
    service.readiness_state_id = 0
    assert service.configured is False


def test_printify_configuration_fails_closed_without_shop():
    service = PrintifyService()
    service.token = "token"
    service.shop_id = ""
    assert service.configured is False


def test_pod_workflow_rejects_unverified_printify_selection_before_external_write():
    product = _product()
    db = _FakeDb(product)
    task = {
        "id": "11111111-1111-1111-1111-111111111111",
        "mission_id": "22222222-2222-2222-2222-222222222222",
        "organization_id": "33333333-3333-3333-3333-333333333333",
        "assigned_agent_id": None,
    }

    with pytest.raises(PODWorkflowBlocked, match="blueprint/provider/image/variant"):
        asyncio.run(
            pod_workflow_service.prepare_draft(
                db,
                task=task,
                source_product_id=product.id,
                print_provider_id=0,
                printify_image_id="",
                variant_ids=[],
                taxonomy_id=1,
            )
        )
