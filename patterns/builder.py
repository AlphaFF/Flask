#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Author: AlphaFF
# @Date:   2018-11-09 13:50:45
# @Email: liushahedi@gmail.com
# @Last Modified by:   AlphaFF
# @Last Modified time: 2018-11-09 17:38:50


class Building:
    def __init__(self):
        self.build_floor()
        self.build_size()

    def build_floor(self):
        raise NotImplementedError

    def build_size(self):
        raise NotImplementedError

    def __repr__(self):
        return 'Floor: {0.floor} | Size: {0.size}'.format(self)


class House(Building):
    def build_floor(self):
        self.floor = 'One'

    def build_size(self):
        self.size = 'big'


class Flat(Building):
    def build_floor(self):
        self.floor = 'more than one'

    def build_size(self):
        self.size = 'small'


class ComplexBuilding:
    def __repr__(self):
        return 'Floor: {0.floor} | size: {0.size}'.format(self)


class ComplexHouse(ComplexBuilding):
    def build_floor(self):
        self.floor = 'One'

    def build_size(self):
        self.size = 'big and fancy'


def construct_building(cls):
    building = cls()
    building.build_floor()
    building.build_size()
    return building


if __name__ == '__main__':
    house = House()
    print(house)
    flat = Flat()
    print(flat)

    complex_house = construct_building(ComplexHouse)
    print(complex_house)
