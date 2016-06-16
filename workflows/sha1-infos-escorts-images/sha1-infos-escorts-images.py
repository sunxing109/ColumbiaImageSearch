import json
import os
from pyspark import SparkContext, SparkConf

def get_list_value(json_x,field_tuple):
    return [x["value"] for x in json_x if x["columnFamily"]==field_tuple[0] and x["qualifier"]==field_tuple[1]]

def to_sha1_key(data):
    cdr_id = data[0]
    json_x = [json.loads(x) for x in data[1].split("\n")]
    sha1 = None
    obj_stored_url = None
    obj_parent = None
    try:
        ## get these fields
        #"info:sha1"
        #"info:obj_stored_url"
        #"info:obj_parent"
        ## maybe also
        #"info:crawl_data.image_id"
        #"info:crawl_data.memex_ht_id"
        sha1 = get_list_value(json_x,("info","sha1"))[0].strip()
        obj_stored_url = get_list_value(json_x,("info","obj_stored_url"))[0].strip()
        obj_parent = get_list_value(json_x,("info","obj_parent"))[0].strip()
        #print key,URL_S3,type(URL_S3)
    except Exception as inst2:
        pass
        #print "[Error] could not get SHA1, obj_stored_url or obj_parent for row {}. {}".format(cdr_id,inst2)
    if cdr_id and sha1 and obj_stored_url and obj_parent:
        ## expose out as:
        #"info:all_cdr_ids"
        #"info:s3_url"
        #"info:all_parent_ids"
        ## maybe also
        #"info:image_ht_ids"
        #"info:ads_ht_id"
        #"info:all_s3_urls"
        #"info:all_original_urls"
        return [(sha1, {"info:all_cdr_ids": [cdr_id], "info:s3_url": [obj_stored_url], "info:all_parent_ids": [cdr_id]})]
    return []

def reduce_sha1_infos(a,b):
    c = dict()
    c["info:all_cdr_ids"] = a["info:all_cdr_ids"]+b["info:all_cdr_ids"]
    c["info:all_parent_ids"] = a["info:all_parent_ids"]+b["info:all_parent_ids"]
    if a["info:s3_url"] and a["info:s3_url"]!=u'None':
        c["info:s3_url"] = a["info:s3_url"]
    else:
        c["info:s3_url"] = b["info:s3_url"]
    return c

def split_sha1_kv(x):
    #print x
    fields_list = [("info","all_cdr_ids"), ("info","s3_url"), ("info","all_parent_ids")]
    out = [(x[0], [x[0], field[0], field[1], ','.join(x[1][field[0]+":"+field[1]])]) for field in fields_list]
    if len(x[1][fields_list[0][0]+":"+fields_list[0][1]])>1:
        print out
    return out

def fill_sha1_infos(sc, hbase_man_in, hbase_man_out):
    in_rdd = hbase_man_in.read_hbase_table()
    tmp_rdd = in_rdd.flatMap(lambda x: to_sha1_key(x)).reduceByKey(reduce_sha1_infos)
    out_rdd = tmp_rdd.flatMap(lambda x: split_sha1_kv(x))
    hbase_man_out.rdd2hbase(out_rdd)

if __name__ == '__main__':
    from hbase_manager import HbaseManager
    job_conf = json.load(open("job_conf.json","rt"))
    print job_conf
    tab_cdrid_name = job_conf["tab_cdrid_name"]
    hbase_host = job_conf["hbase_host"]
    tab_sha1_infos_name = job_conf["tab_sha1_infos_name"]
    sc = SparkContext(appName='sha1_infos_from_'+tab_cdrid_name+'_in_'+tab_sha1_infos_name)
    sc.setLogLevel("ERROR")
    conf = SparkConf()
    hbase_man_in = HbaseManager(sc, conf, hbase_host, tab_cdrid_name)
    hbase_man_out = HbaseManager(sc, conf, hbase_host, tab_sha1_infos_name)
    fill_sha1_infos(sc, hbase_man_in, hbase_man_out)
