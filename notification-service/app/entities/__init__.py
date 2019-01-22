from decimal import Decimal
import datetime as dt
import uuid
import json
import pony.orm as orm

db = orm.Database()

# from app.entities.user import UserEntity
# from app.entities.address import AddressEntity, allowed_address_types
# from app.entities.channel import ChannelEntity
# from app.entities.notification import NotificationEntity
# from app.entities.message import MesaageEntity, allowed_message_states

class EntityCreationError(orm.OrmError):
    def __init__(self, message, inner=None, *args, **kwargs):
        self.message = message
        self.inner = inner
        super().__init__(message, *args, **kwargs)

class EntityHelper:
    def_dumps_indent = 4
    dumps_indent = 4

    def_to_dict_with_collections = True
    to_dict_with_collections = True

    to_dict_related_objects = False
    def_to_dict_related_objects = False

    def_max_relation_depth = 1
    max_relation_depth = None
    relation_depth = None

    converter = None

    @staticmethod
    def default_json_converter(obj):
        ind = EntityHelper.dumps_indent or EntityHelper.def_dumps_indent
        convr = EntityHelper.converter or EntityHelper.default_json_converter

        if isinstance(obj, dt.datetime):
            return obj.isoformat()
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, dict):
            return json.dumps(dict(obj), default=convr, indent=ind)
        if hasattr(obj, '__iter__'): 
            return json.dumps(list(obj), default=convr, indent=ind)
        if isinstance(obj, db.Entity):
            with_coll = EntityHelper.to_dict_with_collections or EntityHelper.def_to_dict_with_collections
            rel_obj = EntityHelper.def_to_dict_related_objects

            if EntityHelper.relation_depth is not None and EntityHelper.max_relation_depth:
                EntityHelper.relation_depth += 1
                if EntityHelper.relation_depth >= EntityHelper.max_relation_depth:
                    rel_obj = False
                else:
                    rel_obj = EntityHelper.to_dict_related_objects or EntityHelper.def_to_dict_related_objects

            _d = obj.to_dict(related_objects=rel_obj, with_collections=with_coll)
            _s = json.dumps(_d, default=convr, indent=ind)
            #, ensure_ascii=False
            return _s #.replace('\\"', '"').replace('\\n', '\n')
        return json.dumps(obj, default=convr, indent=ind)

    @staticmethod
    def to_json(obj, indent=None, converter=None, with_collections=None, 
            related_objects=None, depth=None):
        try:
            if not indent:
                indent = EntityHelper.def_dumps_indent
            EntityHelper.dumps_indent = indent

            if not converter:
                converter = EntityHelper.default_json_converter
            EntityHelper.converter = converter

            if not with_collections:
                with_collections = EntityHelper.def_to_dict_with_collections
            EntityHelper.to_dict_with_collections = with_collections

            if not related_objects:
                related_objects = EntityHelper.def_to_dict_related_objects
            EntityHelper.to_dict_related_objects = related_objects

            if not depth:
                depth = EntityHelper.def_max_relation_depth
            EntityHelper.max_relation_depth = depth
            EntityHelper.relation_depth = 0

            is_entity = isinstance(obj, db.Entity)
            o_dict = None
            if is_entity:
                o_dict = obj.to_dict(
                    with_collections=with_collections, 
                    related_objects=related_objects)
            else:
                o_dict = obj.__dict__
            s = json.dumps(obj=o_dict, default=converter, indent=indent)
            return s
        finally:
            EntityHelper.max_relation_depth = None
            EntityHelper.relation_depth = None

    @staticmethod
    def to_string(o):
        s = "[{0}]:".format(type(o).__name__)
        for k, v in o.__dict__.items():
            is_date = isinstance(v, (dt.datetime, dt.date))
            s += "\n  - {0} ({1}): {2}".format(k, type(v).__name__, 
                                        v.isoformat() if is_date else v)
        return s.rstrip()

class TinyArgValidator():
    @staticmethod
    def isNullOrEmpty(arg):
        if arg is None:
            return True
        if isinstance(arg, str) and len(arg) == 0:
            return True
        return False
    @staticmethod
    def notEmptyStr(arg, arg_name):
        """if {arg} is null or empty, raise "ValueError" with specified {arg_name}"""
        if TinyArgValidator.isNullOrEmpty(arg):
            raise ValueError('you must specify "{}"'
                .format(arg_name if arg_name else ''))