from flask import request, jsonify
from app.services.property_service import PropertyService


class PropertyController:

    @staticmethod
    def create_property():
        try:
            data = request.get_json()
            new_property = PropertyService.create_property(data)

            return jsonify(new_property.to_dict()), 201

        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        except Exception as e:
            return jsonify({"error": "Internal server error"}), 500

    @staticmethod
    def get_all_properties():
        properties = PropertyService.get_all_properties()
        return jsonify([p.to_dict() for p in properties]), 200

    @staticmethod
    def get_property(property_id):
        property = PropertyService.get_property_by_id(property_id)

        if not property:
            return jsonify({"error": "Property not found"}), 404

        return jsonify(property.to_dict()), 200
    

    @staticmethod
    def update_property(property_id):
        data = request.get_json()
        updated_property = PropertyService.update_property(property_id, data)

        if not updated_property:
            return jsonify({"error": "Property not found"}), 404

        return jsonify(updated_property.to_dict()), 200

    @staticmethod
    def delete_property(property_id):
        deleted = PropertyService.delete_property(property_id)

        if not deleted:
            return jsonify({"error": "Property not found"}), 404

        return jsonify({"message": "Property deleted"}), 200