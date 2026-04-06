from app.extensions import db
from app.models.property_model import Property


class PropertyRepository:

    @staticmethod
    def create_property(data):
        new_property = Property(
            title=data["title"],
            address=data["address"],
            price=data["price"],
            operation_type=data["operation_type"],
            status=data.get("status", "available")
        )

        db.session.add(new_property)
        db.session.commit()

        return new_property

    @staticmethod
    def get_all_properties():
        return Property.query.all()

    @staticmethod
    def get_property_by_id(property_id):
        return Property.query.get(property_id)
    

    @staticmethod
    def update_property(property, data):
        property.title = data.get("title", property.title)
        property.address = data.get("address", property.address)
        property.price = data.get("price", property.price)
        property.operation_type = data.get("operation_type", property.operation_type)
        property.status = data.get("status", property.status)

        db.session.commit()
        return property

    @staticmethod
    def delete_property(property):
        db.session.delete(property)
        db.session.commit()