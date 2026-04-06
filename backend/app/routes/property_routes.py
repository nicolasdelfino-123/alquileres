from flask import Blueprint
from app.controllers.property_controller import PropertyController

property_bp = Blueprint("property_bp", __name__)

property_bp.route("/properties", methods=["POST"])(PropertyController.create_property)
property_bp.route("/properties", methods=["GET"])(PropertyController.get_all_properties)
property_bp.route("/properties/<int:property_id>", methods=["GET"])(PropertyController.get_property)
property_bp.route("/properties/<int:property_id>", methods=["PUT"])(PropertyController.update_property)
property_bp.route("/properties/<int:property_id>", methods=["DELETE"])(PropertyController.delete_property)