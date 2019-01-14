
from decimal import Decimal
from datetime import datetime
from pony.orm import *
import uuid

db = Database()
"""db.bind(provider='postgres', 
    user='wr',
    password='KfW9ZvaEJlax1Bx',
    host='localhost',
    database='wrReIdentificationTest',
    port=5432)"""
db.bind(provider='sqlite', filename='db.sqlite', create_db=True, timeout=500)


class Person(db.Entity):
    _table_ = "Person"
    id = PrimaryKey(uuid.UUID, default=uuid.uuid4, column='Id')
    name = Required(str, column='Name')
    age = Required(int, column='Age')
    create_date = Required(datetime, column='CreateDate', default=datetime.utcnow())
    cars = Set('Car')

    def __str__(self):
        return '{0} | {1} | {2} | {3}'.format(self.id, self.name, self.age, self.create_date)

    @property
    @db_session
    def p_cars(self):
        return list(self.cars.select().order_by(lambda c: c.create_date))


class Car(db.Entity):
    _table_ = "Car"
    id = PrimaryKey(uuid.UUID, default=uuid.uuid4, column='Id')
    make = Required(str, column='Make')
    model = Required(str, column='Model')
    create_date = Required(datetime, column='CreateDate', default=datetime.utcnow())
    owner = Required(Person, column='OwnerId')

    def __str__(self):
        return '{0} | {1} | {2} | {3}'.format(self.id, self.make, self.model, self.create_date)


class PersonRepo:
    def __init__(self, data_base, debug=True):
        self.db = data_base
        self.debug = debug
        set_sql_debug(self.debug)
        self.db.generate_mapping(create_tables=True)

    @db_session
    def create_person(self, name, age):
        _p = Person(name=name, age=age)
        print('Created person:\n{0}'.format(_p))
        return _p

    @db_session
    def create_car(self, make, model, owner):
        _c = Car(make=make, model=model, owner=owner)
        print('Created car:\n{0}'.format(_c))
        return _c

    def main(self):
        show(Car)

        with db_session:
            p_kate = Person.get(name='Kate')
            if p_kate is None:
                p_kate = self.create_person('Kate', '37')
            print('p_kate.type = {0}'.format(type(p_kate)))
            self.create_car('Audi', 'R8', p_kate)
            print('p_kate.p_cars.type: {0}'.format(type(p_kate.p_cars)))
            print('p_kate.cars:')
            for c in p_kate.p_cars:
                print('    {0}'.format(c))

        with db_session:
            _p20 = select(p for p in Person if p.age > 20)\
                .order_by(Person.name)\
                .first()
            print('Person: {0}'.format(_p20))
            print('_p20.type = {0}'.format(type(_p20)))

        with db_session:
            _p = Person.get(name='Kate')
            print('_p.type = {0}'.format(type(_p)))
            # show(_p)
            # print('Name: {0}'.format((_p.name)))
            # print('Person: {0}'.format(_p))


r = PersonRepo(db, False)
if __name__ == '__main__':
    r.main()
