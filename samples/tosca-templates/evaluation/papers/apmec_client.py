#!/bin/sh

from apmecclient.v1_0 import client as apmec_client


class ApmecClient(object):
    """Apmec Client class"""

    def __init__(self, sess):
        self.client = apmec_client.Client(session=sess)

    def mesd_create(self, mesd_dict):
        mesd_instance = self.client.create_mesd(body=mesd_dict)
        if mesd_instance:
            return mesd_instance['mesd']['id']
        else:
            return None

    def mesd_get_by_name(self, mesd_name):
        mesd_dict = self.client.list_mesds()
        mesd_list = mesd_dict['mesds']
        mesd_dict = None
        for mesd in mesd_list:
            if mesd['name'] == mesd_name:
                mesd_dict = mesd
        return mesd_dict

    def mesd_get(self, mesd_id):
        mesd_dict = self.client.show_mesd(mesd_id)
        return mesd_dict['mesd']

    def mes_create(self, mes_dict):
        mes_instance = self.client.create_mes(body=mes_dict)
        return mes_instance['mes']

    def mes_get_by_name(self, mes_name):
        mes_dict = self.client.list_mesds()
        mes_list = mes_dict['mess']
        mes_id = None
        for mes in mes_list:
            if mes['name'] == mes_name:
                mes_id = mes['id']
        return mes_id

    def vim_get(self, vim_name):
        vim_dict = self.client.list_vims()
        vim_list = vim_dict['vims']
        vim_info = None
        for vim in vim_list:
            if vim['name'] == vim_name:
                vim_info = vim
        return vim_info

    def mes_get(self, mes_id):
        mes_instance = self.client.show_mes(mes_id)
        return mes_instance['mes']

    def mes_delete_by_name(self, mes_name):
        mes_id = self.mes_get_by_name(mes_name)
        if mes_id:
            self.client.delete_mes(mes_id)

    def mes_delete(self, mes_id):
        return self.client.delete_mes(mes_id)

    def mes_update(self, mes_id, mes_dict):
        return self.client.update_mes(mes_id, mes_dict)

    def mead_create(self, mead_dict):
        mead_instance = self.client.create_mead(body=mead_dict)
        if mead_instance:
            return mead_instance['mead']['id']
        else:
            return None

    def mea_create(self, mea_dict):
        mea_instance = self.client.create_mea(body=mea_dict)
        if mea_instance:
            return mea_instance['mea']['id']
        else:
            return None

    def mea_get(self, mea_id):
        mea_instance = self.client.show_mea(mea_id)
        return mea_instance['mea']

    def mead_get(self, mead_id):
        mead_instance = self.client.show_mead(mead_id)
        return mead_instance['mead']



