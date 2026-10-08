from functools import partial
from flask import Blueprint
from app.controllers.management_controller import ManagementController as Controller
from app.services.management_service import RESOURCES, FINANCIAL

management_bp = Blueprint("management", __name__)

for resource, model in RESOURCES.items():
    # Preserve the existing properties blueprint and URLs.
    if resource == "properties":
        continue
    management_bp.add_url_rule(f"/{resource}", f"{resource}_collection",
        partial(Controller.collection, resource), methods=["GET", "POST"])
    methods = ["GET"] if model in FINANCIAL else ["GET", "PUT", "PATCH", "DELETE"]
    if resource == "contract-tenants":
        methods = ["GET", "DELETE"]
    management_bp.add_url_rule(f"/{resource}/<int:identifier>", f"{resource}_item",
        partial(Controller.item, resource), methods=methods)
    if model in FINANCIAL:
        management_bp.add_url_rule(f"/{resource}/<int:identifier>/cancel", f"{resource}_cancel",
            partial(Controller.cancel, resource), methods=["POST"])

for resource in ("charges", "settlements"):
    management_bp.add_url_rule(f"/{resource}/<int:identifier>/balance", f"{resource}_balance",
        partial(Controller.balance, resource), methods=["GET"])

management_bp.add_url_rule("/persons/<int:identifier>/debts", "tenant_debts", Controller.tenant_debts)
management_bp.add_url_rule("/persons/<int:identifier>/settlements", "owner_balances", Controller.owner_balances)
management_bp.add_url_rule("/dashboard", "dashboard", Controller.dashboard)
for kind in ("expirations", "adjustments"):
    management_bp.add_url_rule(f"/contracts/upcoming-{kind}", f"upcoming_{kind}", partial(Controller.upcoming, kind))

management_bp.add_url_rule("/contracts/<int:identifier>/tenants", "contract_tenants", Controller.contract_tenants, methods=["GET", "POST"])
