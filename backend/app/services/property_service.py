from app.repositories.property_repository import PropertyRepository


class PropertyService:

    @staticmethod
    def create_property(data):
        # Validaciones básicas
        required_fields = ["title", "address", "price", "operation_type"]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Field {field} is required")

        return PropertyRepository.create_property(data)

    @staticmethod
    def get_all_properties():
        return PropertyRepository.get_all_properties()

    @staticmethod
    def get_property_by_id(property_id):
        return PropertyRepository.get_property_by_id(property_id)
    

    @staticmethod
    def update_property(property_id, data):
        property = PropertyRepository.get_property_by_id(property_id)

        if not property:
            return None

        return PropertyRepository.update_property(property, data)

    @staticmethod
    def delete_property(property_id):
        property = PropertyRepository.get_property_by_id(property_id)

        if not property:
            return False

        PropertyRepository.delete_property(property)
        return True