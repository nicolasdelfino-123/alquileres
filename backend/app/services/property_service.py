from app.services.management_service import ManagementService
from app.repositories.property_repository import PropertyRepository


class PropertyService:
    @staticmethod
    def create_property(data):
        return ManagementService.create("properties", data)

    @staticmethod
    def get_all_properties():
        return PropertyRepository.get_all_properties()

    @staticmethod
    def get_property_by_id(property_id):
        return PropertyRepository.get_property_by_id(property_id)

    @staticmethod
    def update_property(property_id, data):
        if not PropertyRepository.get_property_by_id(property_id):
            return None
        return ManagementService.update("properties", property_id, data)

    @staticmethod
    def delete_property(property_id):
        if not PropertyRepository.get_property_by_id(property_id):
            return False
        ManagementService.delete("properties", property_id)
        return True
