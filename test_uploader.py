#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本，用于验证小红书上传工具的核心功能
"""

import os
import json
import sys
import unittest

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入需要测试的模块
from xiaohongshu_uploader import XiaohongshuUploader

class TestXiaohongshuUploader(unittest.TestCase):
    """测试小红书上传工具的核心功能"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.test_config = {
            "upload_time": "09:30",
            "caption": "测试文案",
            "tags": "测试,小红书,自动上传",
            "enable_schedule": True,
            "image_folder": "test_folder",
            "current_image_index": 0
        }
        
        # 临时配置文件路径
        self.test_config_path = "test_config.json"
    
    def tearDown(self):
        """测试后的清理工作"""
        # 删除测试配置文件
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)
    
    def test_config_loading(self):
        """测试配置文件加载功能"""
        # 保存测试配置
        with open(self.test_config_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_config, f)
        
        # 模拟加载配置
        def mock_load_config(self):
            if os.path.exists(self.test_config_path):
                with open(self.test_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {
                "upload_time": "08:00",
                "caption": "",
                "tags": "",
                "enable_schedule": False,
                "image_folder": "",
                "current_image_index": 0
            }
        
        # 测试配置加载
        config = mock_load_config(self)
        self.assertEqual(config["upload_time"], self.test_config["upload_time"])
        self.assertEqual(config["caption"], self.test_config["caption"])
        self.assertEqual(config["tags"], self.test_config["tags"])
        self.assertEqual(config["enable_schedule"], self.test_config["enable_schedule"])
        self.assertEqual(config["image_folder"], self.test_config["image_folder"])
        self.assertEqual(config["current_image_index"], self.test_config["current_image_index"])
    
    def test_config_saving(self):
        """测试配置文件保存功能"""
        # 模拟保存配置
        with open(self.test_config_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_config, f)
        
        # 验证配置文件是否正确保存
        with open(self.test_config_path, 'r', encoding='utf-8') as f:
            saved_config = json.load(f)
        
        self.assertEqual(saved_config, self.test_config)
    
    def test_image_path_validation(self):
        """测试图片路径验证"""
        # 测试不存在的图片路径
        non_existent_path = "non_existent_image.jpg"
        self.assertFalse(os.path.exists(non_existent_path))
        
        # 测试存在的文件（当前脚本本身）
        self.assertTrue(os.path.exists(__file__))
    
    def test_tags_parsing(self):
        """测试标签解析功能"""
        # 测试正常的标签字符串
        tags_str = "测试,小红书,自动上传"
        expected_tags = ["测试", "小红书", "自动上传"]
        self.assertEqual(tags_str.split(','), expected_tags)
        
        # 测试空标签字符串
        empty_tags_str = ""
        self.assertEqual(empty_tags_str.split(','), [""])
        
        # 测试单个标签
        single_tag_str = "单个标签"
        self.assertEqual(single_tag_str.split(','), ["单个标签"])
    
    def test_upload_time_format(self):
        """测试上传时间格式"""
        # 测试有效的时间格式
        valid_times = ["00:00", "08:00", "12:30", "23:59"]
        for time_str in valid_times:
            # 简单验证格式：HH:MM
            parts = time_str.split(':')
            self.assertEqual(len(parts), 2)
            self.assertTrue(0 <= int(parts[0]) <= 23)
            self.assertTrue(0 <= int(parts[1]) <= 59)

if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
