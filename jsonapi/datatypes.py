import enum
import marshmallow


class DataType(enum.Enum):
    """
    Field data types.
    """
    Bool = marshmallow.fields.Bool()
    Integer = marshmallow.fields.Integer()
    Float = marshmallow.fields.Float()
    String = marshmallow.fields.String()
    Date = marshmallow.fields.Date()
    DateTime = marshmallow.fields.DateTime('%Y-%m-%dT%H:%M:%SZ')
    Time = marshmallow.fields.Time()


Bool = DataType.Bool
Integer = DataType.Integer
Float = DataType.Float
String = DataType.String
Date = DataType.Date
DateTime = DataType.DateTime
Time = DataType.Time
