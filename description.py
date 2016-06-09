#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Программа опроса состояния портов коммутаторов различных производителей

import MySQLdb
import gc
import string
import pysnmp
from pysnmp.entity.rfc3413.oneliner import cmdgen
from datetime import datetime

# получаем группу oid 
def get_snmp(host_ip, oid, comm):
    resultSnmp=[]
    cmdGen = cmdgen.CommandGenerator()
    errorIndication, errorStatus, errorIndex, varBindTable = cmdGen.nextCmd(
        cmdgen.CommunityData(comm),
        cmdgen.UdpTransportTarget((host_ip, 161)),
        oid,
        lookupNames=True, lookupValues=True
    )

    if errorIndication:
        print(errorIndication)
        return False
        
    else:
        if errorStatus:
            print('%s at %s' % (
                errorStatus.prettyPrint(),
                errorIndex and varBindTable[-1][int(errorIndex)-1] or '?'
                )
            )
            return False
            
        else:
            for varBindTableRow in varBindTable:
                for name, val in varBindTableRow:
                    #print('%s = %s' % (name.prettyPrint(), val.prettyPrint()))
                    resultSnmp.append(val.prettyPrint())
            return resultSnmp
# Получаем еденичный  oid
def get_one_snmp(host_ip, oid, comm):
    cmdGen = cmdgen.CommandGenerator()
    errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
        cmdgen.CommunityData(comm),
        cmdgen.UdpTransportTarget((host_ip, 161)),oid        
    )
    
    # Check for errors and print out results
    if errorIndication:
        print(errorIndication)
        return False
    else:
        if errorStatus:
            print('%s at %s' % (
                errorStatus.prettyPrint(),
                errorIndex and varBinds[int(errorIndex)-1] or '?'
                )
            )
            return False
        else:
            for name, val in varBinds:
                #print('%s = %s' % (name.prettyPrint(), val.prettyPrint()))
                return (val.prettyPrint())
            
def write_log(text):
    f = open('/var/www/html/ase_cms/media/python/log.txt', 'a')
    f.write(text)
    f.close()
    
            
# Добавление в таблицу результата опроса коммутаторов        
def insert_port(arg1):
   # print ("arg1= ", arg1 )
    insert = """insert into description(com_id, com_name, port, status, speed, description, date_time) values (%s, %s, %s, %s, %s, %s, NOW())"""
    cursor.executemany(insert, arg1)

# Удаление старых записей из таблицы по конкретному коммутатору
def clear_commut(id_1):     

    delstatmt = "DELETE FROM description WHERE com_id = %s"
    cursor.execute(delstatmt, (id_1,))
    db.commit()

def oid_set(ip,comm):
    Desc=[]
    Port=[]
    Status=[]
    Speed=[]
    
    oid_descr=(1,3,6,1,2,1,31,1,1,1,18) # Получаем десткипшен
    Desc = get_snmp(ip, oid_descr, comm) # вызываем функцию 
    
    oid_descr=(1,3,6,1,2,1,31,1,1,1,1) # Получаем имя порта Gi0/1
    Port = get_snmp(ip, oid_descr, comm)

    oid_descr=(1,3,6,1,2,1,2,2,1,8)   # Получаем статус порта
    Status = get_snmp(ip, oid_descr, comm)
    #print Status
    
    oid_descr=(1,3,6,1,2,1,1,5,0)
    NameCom = get_one_snmp(ip, oid_descr, comm)
    
    oid_descr=(1,3,6,1,2,1,2,2,1,5)
    Speed = get_snmp(ip, oid_descr, comm)
    
    return Desc, Port, Status, NameCom, Speed

def select():    
    global cursor, db    
    # соединяемся с базой данных
    db = MySQLdb.connect(host="localhost", user="username", passwd="mypass", db="ase", charset='utf8')
    # формируем курсор
    cursor = db.cursor()
    # запрос к БД
    sql = "SELECT t1.id, t1.model_id, t1.ip, t2.model, t2.comm FROM commutator as t1 LEFT JOIN commutator_model as t2 ON t1.model_id = t2.id WHERE t2.comm IS NOT NULL"
    # выполняем запрос
    cursor.execute(sql) 
    # получаем результат выполнения запроса
    data1 =  cursor.fetchall()
    # перебираем записи
    search_comm(data1)
# закрываем соединение с БД и отключаемся от сервера    
    db.close()
    gc.collect()
    
def search_comm(data):
    for commutator in data:
        # извлекаем данные из записей - в том же порядке, как и в SQL-запросе
        id_com, model_id, ip, model, comm = commutator
        # выводим информацию
        print id_com, ip, model, comm

        # Определяем списки         
        if model=='Cisco ME 3400G-12CS':
            result=[]
            Desc, Port, Status, NameCom, Speed = oid_set(ip, comm)
            clear_commut(id_com) # Очищаем предыдущие записи по дискрипшенам
            if Desc!=False and NameCom!=False:
                for i in range(19):  # По каждому коммутатору 3400 у нас 19 портов 3 виртуальных и 16 реальных
                    result.append((id_com, NameCom, Port[i], Status[i], Speed[i], Desc[i])) # Cisco ME 3400G-12CS Из отдельно взятых списков формируем списки вида: id коммутатора, имя порта, статус, дескрипшен
                insert_port(result) # Записываем новые дескрипшены
            else: 
                data_send=datetime.strftime(datetime.now(), "%Y.%m.%d %H:%M:%S")
                text=u"%s The switch %s %s %s does not transmit data on snmp \n" %(data_send, id_com, ip, model)
                write_log(text)

        if model=='Cisco ME 4924-10GE':
            result=[]
            Desc, Port, Status, NameCom, Speed = oid_set(ip, comm)
            #print NameCom
            clear_commut(id_com) # Очищаем предыдущие записи по дискрипшенам
            if Desc!=False and NameCom!=False:
                for i in range(30):  # По каждому коммутатору 4924 у нас 30 портов 3 виртуальных и 16 реальных
                    result.append((id_com, NameCom, Port[i], Status[i], Speed[i], Desc[i])) # Cisco ME 4924-10GE Из отдельно взятых списков формируем списки вида: id коммутатора, имя порта, статус, дескрипшен
                insert_port(result) # Записываем новые дескрипшены
            else: 
                data_send=datetime.strftime(datetime.now(), "%Y.%m.%d %H:%M:%S")
                text=u"%s The switch %s %s %s does not transmit data on snmp \n" %(data_send, id_com, ip, model)
                write_log(text)
            
        if model=='D-Link  DGS 3120-24SC  DC' or model=='ZTE ZXR 10 5250-28SM':
            result=[]
            Desc, Port, Status, NameCom, Speed = oid_set(ip, comm)
            #print NameCom
            clear_commut(id_com) # Очищаем предыдущие записи по дискрипшенам
            if Desc!=False and NameCom!=False:
                for i in range(24):  # По каждому коммутатору 24 порта
                    result.append((id_com, NameCom, Port[i], Status[i], Speed[i], Desc[i])) # D-Link  DGS 3120-24SC  DC Из отдельно взятых списков формируем списки вида: id коммутатора, имя порта, статус, дескрипшен
                insert_port(result) # Записываем новые дескрипшены
            else:
                data_send=datetime.strftime(datetime.now(), "%Y.%m.%d %H:%M:%S")
                text=u"%s The switch %s %s %s does not transmit data on snmp \n" %(data_send, id_com, ip, model)
                write_log(text)
                
        if model=='D-Link  DGS 3420-26SC  DC':
            result=[]
            Desc, Port, Status, NameCom, Speed = oid_set(ip, comm)
            #print NameCom
            clear_commut(id_com) # Очищаем предыдущие записи по дискрипшенам
            if Desc!=False and NameCom!=False:
                for i in range(26):  # По каждому коммутатору 26 портов
                    result.append((id_com, NameCom, Port[i], Status[i], Speed[i], Desc[i])) # D-Link  DGS 3120-24SC  DC Из отдельно взятых списков формируем списки вида: id коммутатора, имя порта, статус, дескрипшен
                insert_port(result) # Записываем новые дескрипшены
            else:
                data_send=datetime.strftime(datetime.now(), "%Y.%m.%d %H:%M:%S")
                text=u"%s The switch %s %s %s does not transmit data on snmp \n" %(data_send, id_com, ip, model)
                write_log(text)  
        
        if model=='ZTE ZXR 10 2928-SI DC' or model=='ZTE ZXR 10 2928E AC':
            result=[]
            Desc, Port, Status, NameCom, Speed = oid_set(ip, comm)
            #print NameCom
            clear_commut(id_com) # Очищаем предыдущие записи по дискрипшенам
            if Desc!=False and NameCom!=False:
                for i in range(28):  # По каждому коммутатору 26 портов
                    result.append((id_com, NameCom, Port[i], Status[i], Speed[i], Desc[i])) # D-Link  DGS 3120-24SC  DC Из отдельно взятых списков формируем списки вида: id коммутатора, имя порта, статус, дескрипшен
                insert_port(result) # Записываем новые дескрипшены
            else:
                data_send=datetime.strftime(datetime.now(), "%Y.%m.%d %H:%M:%S")
                text=u"%s The switch %s %s %s does not transmit data on snmp \n" %(data_send, id_com, ip, model)
                write_log(text)
            
                
        if model=='ZTE ZXR 10 2936-FI':
            result=[]
            Desc, Port, Status, NameCom, Speed = oid_set(ip, comm)
            #print NameCom
            clear_commut(id_com) # Очищаем предыдущие записи по дискрипшенам
            if Desc!=False and NameCom!=False:
                for i in range(36):  # По каждому коммутатору 26 портов
                    result.append((id_com, NameCom, Port[i], Status[i], Speed[i], Desc[i])) # D-Link  DGS 3120-24SC  DC Из отдельно взятых списков формируем списки вида: id коммутатора, имя порта, статус, дескрипшен
                insert_port(result) # Записываем новые дескрипшены
            else:
                data_send=datetime.strftime(datetime.now(), "%Y.%m.%d %H:%M:%S")
                text=u"%s The switch %s %s %s does not transmit data on snmp \n" %(data_send, id_com, ip, model)
                write_log(text)       
        
        if model=='Huawei S2328P':
            result=[]
            Desc, Port, Status, NameCom, Speed = oid_set(ip, comm)
            clear_commut(id_com) # Очищаем предыдущие записи по дискрипшенам
            if Desc!=False and NameCom!=False:
                for i in range(32):  # По каждому коммутатору 32 порта
                    result.append((id_com, NameCom, Port[i], Status[i], Speed[i], Desc[i])) # D-Link  DGS 3120-24SC  DC Из отдельно взятых списков формируем списки вида: id коммутатора, имя порта, статус, дескрипшен
            #    print result
                insert_port(result) # Записываем новые дескрипшены
            else:
                data_send=datetime.strftime(datetime.now(), "%Y.%m.%d %H:%M:%S")
                text=u"%s The switch %s %s %s does not transmit data on snmp \n" %(data_send, id_com, ip, model)
                write_log(text) 
                
                
if __name__ == '__main__':
    select()
   