from dataclasses import dataclass


@dataclass
class UserNRega:
    reg: str


persis_data = {}


def get_reg(user_id: int):
    global persis_data
    return persis_data[user_id].reg


def put_reg(user_id: int, reg: str):
    global persis_data
    persis_data[user_id] = UserNRega(reg)
