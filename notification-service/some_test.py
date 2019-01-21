def q(m=None, *args, **kwargs):
    print(m)
    print(args)
    print(kwargs)

q(1,2,3,4,5,q=1,w="s",f=0.1)
q()
q("ss",q=1,a="a")

# #from notification_repo import *
# import uuid
# #from pony import orm
# import Domain.models as orm
# import json

# e = orm.OrmError()

# orm.default_bus_message_sender = None

# class BaseEntity(orm.db.Entity):
#     #service_hidden_filed = orm.Optional(bool, ccolumn="service_hidden_filed", default=None, nullable=True)
#     id = orm.PrimaryKey(uuid.UUID, column="Id", default=uuid.uuid4)
#     def to_view(self, with_collections=True, related_objects=False, exclude=None):
#         """return self.to_dict()"""
#         #exclude="service_hidden_filed"
#         return self.to_dict(with_collections=with_collections, 
#                             related_objects=related_objects,
#                             exclude=exclude)

# class Pen(BaseEntity):
#     color = orm.Required(str, column="Color")
#     penal = orm.Optional(lambda: Bag, column="PenalId")
# class Bag(BaseEntity):
#     name = orm.Required(str, column="Name")
#     items = orm.Set(lambda: Pen)

# f = "notifications2.sqlite"
# orm.db.bind(provider="sqlite", filename=f, create_db=True)
# orm.db.generate_mapping(create_tables=True)
# orm.DbInitor.seed()

# with orm.db_session:
#     bag = Bag.get(name="bag1")
#     if not bag:
#         bag = Bag(name="bag1")

#     p = Pen.get(color="red")
#     if not p:
#         p = Pen(color="red", penal=bag)
#     d = bag.to_view()
#     print(d)

#     # l = list(select(a for a in AddressEntity))
#     # js = {"date": [a.to_dict() for a in l]}
#     # print(json.dumps(js, indent=4, default=EntityHelper.json_convert_default))

#     # u = UserEntity.get(name='some_man_1')
#     # print(u.to_dict())
#     # print(EntityHelper.to_json(u))

#     # al = [a for a in orm.AddressEntity.select()]
#     # for a in al:
#     #     print(orm.EntityHelper.to_json(a))

#     # for u in UserEntity.select():
#     #     #j = u.to_json()
#     #     #d = u.to_dict(related_objects=True, with_collections=True)
#     #     #print(d)
#     #     #print(EntityHelper.to_json(u))
#     #     #print(json.dumps(d, default=EntityHelper.default_json_converter, indent=2))
#     #     print(EntityHelper.to_json(u))

#     # def_ch = ChannelEntity.get(name='default')
#     # a_list = [a for a in def_ch.addresses.select()]
#     # for a in a_list:
#     #     print(EntityHelper.to_json(a))






# # r = RepoFactory.get()

# # for a in r.get_addresses(type_id="email"):
# #     print(a)

# # a = None
# # if a:
# #     print(a)


# # allowed_address_types=[0,1,None]
# # type_id = None
# # if type_id is None or type_id not in allowed_address_types:
# #     print(1)

# # if type_id not in allowed_address_types:
# #     print(1)

# # address_ids = [444, 555]
# # if address_ids is not None and len(address_ids) > 0:
# #     print(1)
# # else:
# #     print(0)

# # if address_ids and len(address_ids) > 1:
# #     print(1)
# # else:
# #     print(0)

# # class Bar(object):

# #     @classmethod
# #     def bar(cls, i=None):
# #         # code
# #         print(cls.__name__, i)

# # class Foo(Bar):
# #     # code
# #     pass

# # Bar.bar(1111)
# # Foo.bar(777)

# # class TestClassExample:
# #     def q(self):
# #         print(__class__)
# #         print(__name__)
# #         print(__class__.__name__)
# #     def log(self, msg, *args, **kwargs):
# #         if len(args)>0:
# #             msg = msg.format(*args)
# #         else:
# #             msg = msg.format(**kwargs)
# #         print(msg)
# # t = TestClassExample()
# # #t.q()
# # t.log('qqqq {} www {}', 1, 2)
# # t.log('qqqq {0} www {0} eee {1}', 1, 2)
# # t.log('qqqq {a} www {b} eee {c}', a=1, b=2, d=3)

# # u = User(name="q", email="some@email.com")
# # print(u)
# # js = u.to_json(4)
# # print(type(js))
# # print(js)

# # r = RepoFactory.get()
# # q = r.add_user(name='ww', phone='333')
# # print(q)
# # for i in r.get_users():
# #     print('{0}'.format(i))

# #a = array([0 for x in range(5)])
# #a = array()
# #print(type(a))

# ##a.append(1)
# #print(a)
# #print(type(a))
# #a.append('q')
# #print(a)