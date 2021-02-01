#
# Copyright(c) 2021 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import ctypes
from enum import Enum


class RequestCode(Enum):
    START_CACHE_CODE = ctypes.c_uint(21).value
    STOP_CACHE_CODE = ctypes.c_uint(2).value
    SET_CACHE_STATE_CODE = ctypes.c_uint(3).value
    INSERT_CORE_CODE = ctypes.c_uint(22).value
    REMOVE_CORE_CODE = ctypes.c_uint(23).value
    RESET_STATS_CODE = ctypes.c_uint(6).value
    FLUSH_CACHE_CODE = ctypes.c_uint(9).value
    INTERRUPT_FLUSHING_CODE = ctypes.c_uint(10).value
    FLUSH_CORE_CODE = ctypes.c_uint(11).value
    CACHE_INFO_CODE = ctypes.c_uint(24).value
    CORE_INFO_CODE = ctypes.c_uint(25).value
    PARTITION_INFO_CODE = ctypes.c_uint(14).value
    PARTITION_SET_CODE = ctypes.c_uint(15).value
    GET_CACHE_COUNT_CODE = ctypes.c_uint(16).value
    LIST_CACHE_CODE = ctypes.c_uint(17).value
    UPGRADE_CODE = ctypes.c_uint(19).value
    GET_CORE_POOL_COUNT_CODE = ctypes.c_uint(26).value
    GET_CORE_POOL_PATHS_CODE = ctypes.c_uint(27).value
    CORE_POOL_REMOVE_CODE = ctypes.c_uint(28).value
    CACHE_CHECK_DEVICE_CODE = ctypes.c_uint(29).value
    SET_CORE_PARAM_CODE = ctypes.c_uint(30).value
    GET_CORE_PARAM_CODE = ctypes.c_uint(31).value
    SET_CACHE_PARAM_CODE = ctypes.c_uint(32).value
    GET_CACHE_PARAM_CODE = ctypes.c_uint(33).value
    GET_STATS_CODE = ctypes.c_uint(34).value
    PURGE_CACHE_CODE = ctypes.c_uint(35).value
    PURGE_CORE_CODE = ctypes.c_uint(36).value


KiB = ctypes.c_ulonglong(1024).value
MAX_STR_LEN = 4096
MAX_ELEVATOR_NAME = 16


class InitCache(Enum):
    CACHE_INIT_NEW = ctypes.c_uint8(0).value
    CACHE_INIT_LOAD = ctypes.c_uint8(1).value


class CacheMode(Enum):
    ocf_cache_mode_wt = ctypes.c_int(0).value
    ocf_cache_mode_wb = ctypes.c_int(1).value
    ocf_cache_mode_wa = ctypes.c_int(2).value
    ocf_cache_mode_pt = ctypes.c_int(3).value
    ocf_cache_mode_wi = ctypes.c_int(4).value
    ocf_cache_mode_wo = ctypes.c_int(5).value
    default = ocf_cache_mode_wt


class EvictionPolicy(Enum):
    ocf_promotion_always = ctypes.c_int(0).value
    ocf_promotion_nhit = ctypes.c_int(1).value
    ocf_promotion_max = ctypes.c_int(2).value
    default = ocf_promotion_always


class CacheLineSize(Enum):
    ocf_cache_line_size_4 = ctypes.c_ulonglong(4).value * KiB
    ocf_cache_line_size_8 = ctypes.c_ulonglong(8).value * KiB
    ocf_cache_line_size16 = ctypes.c_ulonglong(16).value * KiB
    ocf_cache_line_size_32 = ctypes.c_ulonglong(32).value * KiB
    ocf_cache_line_size_64 = ctypes.c_ulonglong(64).value * KiB
    default = ocf_cache_line_size_4

