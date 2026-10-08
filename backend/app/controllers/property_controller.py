from app.controllers.management_controller import ManagementController


class PropertyController:
    @staticmethod
    def create_property():
        return ManagementController.collection("properties")

    @staticmethod
    def get_all_properties():
        return ManagementController.collection("properties")

    @staticmethod
    def get_property(property_id):
        return ManagementController.item("properties", property_id)

    @staticmethod
    def update_property(property_id):
        return ManagementController.item("properties", property_id)

    @staticmethod
    def delete_property(property_id):
        return ManagementController.item("properties", property_id)
