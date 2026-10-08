import json
from decimal import Decimal
from flask import request, jsonify
from app.services.management_service import (ManagementService, FinanceService, RESOURCES,
                                            APIError, get_record, serialize)
from app.services.report_service import ReportService


def json_body():
    if not request.is_json:
        raise APIError("Se requiere Content-Type application/json")
    try:
        data = json.loads(request.get_data(), parse_float=Decimal,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (ValueError, UnicodeDecodeError):
        raise APIError("JSON inválido") from None
    if not isinstance(data, dict):
        raise APIError("Se requiere un objeto JSON")
    return data


class ManagementController:
    @staticmethod
    def collection(resource):
        if request.method == "GET":
            return jsonify([serialize(r) for r in ManagementService.list(resource, request.args)])
        record = ManagementService.create(resource, json_body())
        return jsonify(serialize(record)), 201

    @staticmethod
    def item(resource, identifier):
        if request.method == "GET":
            return jsonify(serialize(get_record(RESOURCES[resource], identifier)))
        if request.method == "DELETE":
            ManagementService.delete(resource, identifier)
            return jsonify({"message": "Property deleted" if resource == "properties" else "Registro eliminado"})
        record = ManagementService.update(resource, identifier, json_body())
        return jsonify(serialize(record))

    @staticmethod
    def cancel(resource, identifier):
        return jsonify(serialize(FinanceService.cancel(resource, identifier, json_body())))

    @staticmethod
    def balance(resource, identifier):
        record = get_record(RESOURCES[resource], identifier)
        return jsonify(serialize(record))

    @staticmethod
    def tenant_debts(identifier):
        return jsonify(ReportService.tenant_debts(identifier))

    @staticmethod
    def owner_balances(identifier):
        return jsonify(ReportService.owner_balances(identifier))

    @staticmethod
    def dashboard():
        return jsonify(ReportService.dashboard(request.args))

    @staticmethod
    def upcoming(kind):
        return jsonify(ReportService.upcoming(kind, request.args))

    @staticmethod
    def contract_tenants(identifier):
        from app.services.contract_service import ContractService
        if request.method == "GET":
            return jsonify(ContractService.tenants(identifier))
        data = json_body()
        if set(data) != {"person_id"}:
            raise APIError("Se requiere únicamente person_id")
        record = ManagementService.create("contract-tenants", {"contract_id": identifier, **data})
        return jsonify(serialize(record)), 201
