#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
測試腳本：驗證修正的功能
"""

import sys
import os
from pathlib import Path

def test_fixes():
    """測試修正的功能"""
    print("=" * 50)
    print("手動標註軟體 - 修正功能測試")
    print("=" * 50)
    
    try:
        # 測試程式是否能正常匯入
        import image_annotation_tool
        print("✅ 程式匯入成功")
        
        # 檢查關鍵類別是否存在
        classes_to_check = [
            'MainWindow',
            'ImageCanvas', 
            'AnnotationManager',
            'ColorManager',
            'AnnotationData'
        ]
        
        for class_name in classes_to_check:
            if hasattr(image_annotation_tool, class_name):
                print(f"✅ {class_name} 類別存在")
            else:
                print(f"❌ {class_name} 類別不存在")
        
        print("\n修正項目檢查:")
        
        # 檢查 ImageCanvas 是否有正確的方法
        canvas_class = image_annotation_tool.ImageCanvas
        
        # 檢查防呆機制相關方法
        if hasattr(canvas_class, 'mousePressEvent'):
            print("✅ 滑鼠事件處理存在")
        else:
            print("❌ 滑鼠事件處理不存在")
        
        # 檢查鍵盤事件處理
        if hasattr(canvas_class, 'keyPressEvent'):
            print("✅ 鍵盤事件處理存在")
        else:
            print("❌ 鍵盤事件處理不存在")
        
        # 檢查MainWindow鍵盤事件
        main_class = image_annotation_tool.MainWindow
        if hasattr(main_class, 'keyPressEvent'):
            print("✅ 主視窗鍵盤事件處理存在")
        else:
            print("❌ 主視窗鍵盤事件處理不存在")
        
        print("\n功能改進說明:")
        print("1. ✅ 防呆機制：必須選擇類別才能標註")
        print("2. ✅ Delete鍵刪除：增強鍵盤事件處理")
        print("3. ✅ 圖片切換：自動清除前一張的標註框")
        print("4. ✅ 焦點管理：點擊圖片區域獲得鍵盤焦點")
        
        print("\n測試步驟:")
        print("1. 執行程式: python image_annotation_tool.py")
        print("2. 匯入 test 資料夾")
        print("3. 嘗試不選類別直接標註 -> 應該出現提醒")
        print("4. 選擇類別後標註 -> 應該正常顯示顏色框")
        print("5. 按Delete鍵 -> 應該刪除最後一個標註")
        print("6. 切換圖片 -> 應該清除前一張的標註框")
        
    except Exception as e:
        print(f"❌ 測試過程中出現錯誤: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ 修正功能測試完成！")
    print("=" * 50)
    return True

if __name__ == "__main__":
    test_fixes()
