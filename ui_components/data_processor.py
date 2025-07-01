# -*- coding: utf-8 -*-
"""数据处理模块 - 负责数据预处理、清洗和标准化"""

import pandas as pd
import logging
from typing import Optional, List, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class DataProcessor:
    """数据处理器类"""
    
    def __init__(self):
        self.field_mapping = {
            # SVN字段映射
            'svn_author': 'author',
            'svn_message': 'commit_message',
            'svn_date': 'reviewed_at',
            'repository': 'project_name',
            'repo_name': 'project_name',
            'commit_author': 'author',
            'message': 'commit_message',
            'timestamp': 'reviewed_at'
        }
        
        self.time_fields = ['reviewed_at', 'created_at', 'updated_at', 'commit_date', 'svn_date', 'timestamp']
    
    def preprocess_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据预处理 - 清理和标准化数据，兼容SVN/GitLab/GitHub字段"""
        if df.empty:
            return df
        
        # 应用字段映射
        df = self._apply_field_mapping(df)
        
        # 处理时间字段
        df = self._process_time_fields(df)
        
        # 清理数据字段
        df = self._clean_data_fields(df)
        
        # 记录处理结果
        self._log_processing_results(df)
        
        return df
    
    def _apply_field_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """应用字段映射"""
        for old_field, new_field in self.field_mapping.items():
            if old_field in df.columns and new_field not in df.columns:
                df[new_field] = df[old_field]
        return df
    
    def _process_time_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理时间字段"""
        for time_field in self.time_fields:
            if time_field in df.columns:
                try:
                    if df[time_field].dtype == 'object':
                        # 尝试直接解析
                        df['datetime'] = pd.to_datetime(df[time_field], errors='coerce')
                        # 如果失败，尝试时间戳格式
                        if df['datetime'].isna().all():
                            df['datetime'] = pd.to_datetime(df[time_field], unit='s', errors='coerce')
                    elif pd.api.types.is_numeric_dtype(df[time_field]):
                        # 数字类型，假设是时间戳
                        df['datetime'] = pd.to_datetime(df[time_field], unit='s', errors='coerce')
                    else:
                        # 已经是datetime类型
                        df['datetime'] = df[time_field]
                    
                    # 如果成功解析到时间，跳出循环
                    if not df['datetime'].isna().all():
                        break
                except Exception as e:
                    logger.warning(f"时间字段 {time_field} 处理失败: {e}")
                    continue
        
        # 如果没有找到任何有效的时间字段，创建一个空的datetime列
        if 'datetime' not in df.columns:
            df['datetime'] = pd.NaT
        
        return df
    
    def _clean_data_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理数据字段"""
        # 清理评分字段 - 优先从review_result中提取，而非直接使用数据库的score字段
        if 'score' in df.columns and 'review_result' in df.columns:
            # 如果score为0或缺失，尝试从review_result中提取
            extracted_scores = df.apply(lambda row: self._extract_score_from_review(row), axis=1)
            # 只有当提取到有效评分时才更新
            valid_extracted = extracted_scores[extracted_scores > 0]
            if not valid_extracted.empty:
                df.loc[valid_extracted.index, 'score'] = valid_extracted
            
            df['score'] = pd.to_numeric(df['score'], errors='coerce').fillna(0)
        elif 'score' in df.columns:
            df['score'] = pd.to_numeric(df['score'], errors='coerce').fillna(0)
        elif 'review_result' in df.columns:
            # 如果没有score列，从review_result中提取
            df['score'] = df['review_result'].apply(self._extract_score_from_review)
        
        # 清理作者字段
        if 'author' in df.columns:
            df['author'] = df['author'].fillna('未知作者').astype(str)
        
        # 清理项目名称字段
        if 'project_name' in df.columns:
            df['project_name'] = df['project_name'].fillna('未知项目').astype(str)
        
        # 清理代码变更字段
        for field in ['additions', 'deletions', 'additions_count', 'deletions_count']:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0)
        
        return df
    
    def _log_processing_results(self, df: pd.DataFrame):
        """记录处理结果"""
        logger.info(f"数据预处理完成:")
        logger.info(f"- 数据行数: {len(df)}")
        logger.info(f"- 数据列: {list(df.columns)}")
        if 'datetime' in df.columns:
            logger.info(f"- 时间字段有效数据: {df['datetime'].notna().sum()}")
            if df['datetime'].notna().any():
                logger.info(f"- 时间范围: {df['datetime'].min()} 到 {df['datetime'].max()}")
        if 'project_name' in df.columns:
            logger.info(f"- 项目统计: {df['project_name'].value_counts().head(3).to_dict()}")
    
    def apply_filters(self, df: pd.DataFrame, authors: Optional[List[str]] = None, 
                     projects: Optional[List[str]] = None, 
                     score_range: Tuple[int, int] = (0, 100)) -> pd.DataFrame:
        """应用筛选条件"""
        if df.empty:
            return df
        
        # 作者筛选
        if authors and 'author' in df.columns:
            df = df[df['author'].isin(authors)]
        
        # 项目筛选
        if projects and 'project_name' in df.columns:
            df = df[df['project_name'].isin(projects)]
        
        # 评分筛选
        if score_range != (0, 100) and 'score' in df.columns:
            df = df[(df['score'] >= score_range[0]) & (df['score'] <= score_range[1])]
        
        return df
    
    def get_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """获取数据摘要信息"""
        if df.empty:
            return {
                'total_records': 0,
                'avg_score': 0,
                'unique_authors': 0,
                'unique_projects': 0,
                'date_range': None
            }
        
        summary = {
            'total_records': len(df),
            'avg_score': df['score'].mean() if 'score' in df.columns else 0,
            'unique_authors': df['author'].nunique() if 'author' in df.columns else 0,  
            'unique_projects': df['project_name'].nunique() if 'project_name' in df.columns else 0,
        }
        
        # 添加时间范围信息
        if 'datetime' in df.columns and df['datetime'].notna().any():
            summary['date_range'] = (df['datetime'].min(), df['datetime'].max())
        else:
            summary['date_range'] = None
            
        return summary
    
    def _extract_score_from_review(self, row):
        """从审查结果中提取AI评分"""
        import re
        
        # 如果已有有效评分且大于0，直接返回
        if 'score' in row and pd.notna(row['score']) and row['score'] > 0:
            return row['score']
        
        # 从review_result中提取评分
        review_result = row.get('review_result', '')
        if not review_result or pd.isna(review_result):
            return 0
        
        # 使用正则表达式提取评分
        score_patterns = [
            r"总分[:：]\s*(\d+)分?",  # 总分：85分 或 总分: 85
            r"评分[:：]\s*(\d+)分?",  # 评分：85分
            r"得分[:：]\s*(\d+)分?",  # 得分：85分
            r"分数[:：]\s*(\d+)分?",  # 分数：85分
            r"(\d+)\s*分",          # 85分
        ]
        
        for pattern in score_patterns:
            match = re.search(pattern, str(review_result))
            if match:
                try:
                    score = int(match.group(1))
                    # 确保评分在合理范围内
                    if 0 <= score <= 100:
                        return score
                except (ValueError, IndexError):
                    continue
        
        return 0
