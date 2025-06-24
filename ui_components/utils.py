"""
UI工具函数模块
"""

import datetime
import pandas as pd
import streamlit as st
from biz.service.review_service import ReviewService

def get_available_authors(review_types):
    """获取可用的作者列表"""
    authors = set()
    try:
        review_service = ReviewService()
        for review_type in review_types:
            result = review_service.get_review_statistics(
                review_type=review_type,
                start_date=None,
                end_date=None
            )
            if result.get('success') and result.get('data'):
                for record in result['data']:
                    if record.get('author'):
                        authors.add(record['author'])
    except Exception as e:
        st.error(f"获取作者列表失败: {e}")
    
    return sorted(list(authors))

def get_available_projects(review_types):
    """获取可用的项目列表"""
    projects = set()
    try:
        review_service = ReviewService()
        for review_type in review_types:
            result = review_service.get_review_statistics(
                review_type=review_type,
                start_date=None,
                end_date=None
            )
            if result.get('success') and result.get('data'):
                for record in result['data']:
                    if record.get('project'):
                        projects.add(record['project'])
    except Exception as e:
        st.error(f"获取项目列表失败: {e}")
    
    return sorted(list(projects))

def format_timestamp(timestamp):
    """格式化时间戳"""
    try:
        if isinstance(timestamp, str):
            dt = pd.to_datetime(timestamp)
        else:
            dt = timestamp
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(timestamp)

def get_platform_status(config_manager):
    """获取平台状态"""
    try:
        env_config = config_manager.get_env_config()
        
        platforms = {
            'svn': env_config.get('SVN_CHECK_ENABLED', '0') == '1',
            'gitlab': env_config.get('GITLAB_ENABLED', '0') == '1',
            'github': env_config.get('GITHUB_ENABLED', '0') == '1'
        }
        
        return platforms
    except Exception:
        return {'svn': False, 'gitlab': False, 'github': False}

def get_review_stats(platforms):
    """获取审查统计数据"""
    review_stats = {}
    review_service = ReviewService()
    
    # 获取各类型的统计数据
    if platforms.get('gitlab'):
        for review_type in ['mr', 'push']:
            try:
                result = review_service.get_review_statistics(review_type=review_type)
                if result.get('success') and result.get('data'):
                    review_stats[f'{review_type}_count'] = len(result['data'])
                else:
                    review_stats[f'{review_type}_count'] = 0
            except:
                review_stats[f'{review_type}_count'] = 0
    
    if platforms.get('svn'):
        try:
            result = review_service.get_review_statistics(review_type='svn')
            if result.get('success') and result.get('data'):
                review_stats['svn_count'] = len(result['data'])
            else:
                review_stats['svn_count'] = 0
        except:
            review_stats['svn_count'] = 0
    
    if platforms.get('github'):
        try:
            result = review_service.get_review_statistics(review_type='github')
            if result.get('success') and result.get('data'):
                review_stats['github_count'] = len(result['data'])
            else:
                review_stats['github_count'] = 0
        except:
            review_stats['github_count'] = 0
    
    return review_stats
