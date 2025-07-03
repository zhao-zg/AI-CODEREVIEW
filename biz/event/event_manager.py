from blinker import Signal

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity, SvnReviewEntity
from biz.service.review_service import ReviewService
from biz.utils.im import notifier
from biz.utils.default_config import get_env_with_default

# 定义全局事件管理器（事件信号）
event_manager = {
    "merge_request_reviewed": Signal(),
    "push_reviewed": Signal(),
    "svn_reviewed": Signal(),
}


def _get_ai_score(review_result):
    """从审查结果中提取AI评分"""
    import re
    if not review_result:
        return "未知"
    
    # 匹配总分的多种格式
    score_patterns = [
        r"总分[:：]\s*(\d+)分?",
        r"总分 \(Total Score\)[:：]\s*(\d+)分?",
        r"评分[:：]\s*(\d+)分?", 
        r"得分[:：]\s*(\d+)分?",
        r"分数[:：]\s*(\d+)分?",
        r"分值[:：]\s*(\d+)分?",
    ]
    
    for pattern in score_patterns:
        match = re.search(pattern, review_result)
        if match:
            score = match.group(1)
            # 验证分数范围合理性
            try:
                score_int = int(score)
                if 0 <= score_int <= 100:
                    return score
            except ValueError:
                continue
    
    return "未知"


def _get_score_emoji(score):
    """根据评分获取对应的emoji"""
    if score == "未知":
        return "⚪"
    
    try:
        score_int = int(score)
        # 处理超出正常范围的分数
        if score_int > 100 or score_int < 0:
            return "⚪"
        elif score_int >= 90:
            return "🟢"  # 优秀
        elif score_int >= 80:
            return "🟢"  # 良好
        elif score_int >= 70:
            return "🟡"  # 一般
        elif score_int >= 60:
            return "🟠"  # 需要改进
        else:
            return "🔴"  # 存在问题
    except (ValueError, TypeError):
        return "⚪"


def _get_simplified_review(review_result):
    """获取简化的审查评论 - 最终优化版本"""
    import re
    
    if not review_result:
        return "暂无评论"
    
    # 清理和标准化审查结果
    review_text = str(review_result).strip()
    
    # 移除常见的格式标记和多余空白
    review_text = review_text.replace('**', '').replace('*', '').replace('#', '')
    review_text = re.sub(r'\s+', ' ', review_text)
    
    # 提取关键信息的策略（按优先级）
    
    # 1. 优先提取总结性评价（多种表达方式）
    summary_patterns = [
        r"总结[:：]\s*([^。！？\n]+[。！？]?)",
        r"总体评价[:：]\s*([^。！？\n]+[。！？]?)",
        r"整体评价[:：]\s*([^。！？\n]+[。！？]?)",
        r"综合评价[:：]\s*([^。！？\n]+[。！？]?)",
        r"总体[:：]\s*([^。！？\n]+[。！？]?)",
        r"整体[:：]\s*([^。！？\n]+[。！？]?)",
        r"综合[:：]\s*([^。！？\n]+[。！？]?)",
    ]
    
    for pattern in summary_patterns:
        match = re.search(pattern, review_text)
        if match:
            summary = match.group(1).strip()
            if len(summary) > 8 and not summary.startswith('代码'):
                return _truncate_text(summary, 80)
    
    # 2. 提取"建议"相关的关键评价
    advice_patterns = [
        r"建议[:：]\s*([^。！？\n]+[。！？]?)",
        r"推荐[:：]\s*([^。！？\n]+[。！？]?)",
        r"应该[:：]\s*([^。！？\n]+[。！？]?)",
    ]
    
    for pattern in advice_patterns:
        match = re.search(pattern, review_text)
        if match:
            advice = match.group(1).strip()
            if len(advice) > 10:
                return _truncate_text(f"建议{advice}", 80)
    
    # 3. 寻找包含评价性质的完整句子（优先级更高的关键词）
    high_priority_keywords = ['质量良好', '质量优秀', '质量达标', '符合合并', '可以合并', '推荐合并', '满足上线', '达到标准']
    sentences = re.split(r'[。！？\n]', review_text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if (len(sentence) > 8 and 
            any(keyword in sentence for keyword in high_priority_keywords)):
            return _truncate_text(sentence, 80)
    
    # 4. 寻找一般评价性质的句子
    evaluation_keywords = ['质量', '良好', '合格', '达标', '优秀', '不错', '可以', '符合', '满足', '有效', '正确']
    
    for sentence in sentences:
        sentence = sentence.strip()
        if (len(sentence) > 12 and 
            any(keyword in sentence for keyword in evaluation_keywords) and
            not sentence.startswith(('代码', '文件', '本次', '检查', '审查', '提交'))):
            return _truncate_text(sentence, 80)
    
    # 5. 提取总分之前的关键评价句
    if '总分' in review_text:
        before_score = review_text.split('总分')[0].strip()
        # 查找包含关键词的句子，从后往前找
        key_phrases = ['质量', '良好', '合格', '达标', '优秀', '需要', '建议', '可以', '应该', '有效', '正确']
        before_sentences = re.split(r'[。！？\n]', before_score)
        
        for sentence in reversed(before_sentences):
            sentence = sentence.strip()
            if (len(sentence) > 12 and 
                any(phrase in sentence for phrase in key_phrases) and
                not sentence.startswith(('代码', '文件', '本次', '检查', '审查', '提交'))):
                return _truncate_text(sentence, 80)
    
    # 6. 降级处理：找第一句有实际内容的句子
    for sentence in sentences:
        sentence = sentence.strip()
        if (len(sentence) > 8 and 
            not sentence.startswith(('代码审查', '审查完成', '检查完成', '分析完成', '提交审查', '本次提交', '变更分析')) and
            not re.match(r'^\d+\.', sentence) and  # 排除编号列表
            not sentence.endswith('：') and  # 排除标题
            not sentence.startswith('- ')):  # 排除列表项
            return _truncate_text(sentence, 80)
    
    # 7. 最后降级：取前80个字符
    cleaned = re.sub(r'\s+', ' ', review_text[:100]).strip()
    return _truncate_text(cleaned, 80) if cleaned else "暂无具体评价"


def _truncate_text(text, max_length=80):
    """智能截断文本"""
    if len(text) <= max_length:
        return text
    
    # 尝试在句号、感叹号、问号处截断
    for punct in ['。', '！', '？']:
        pos = text[:max_length].rfind(punct)
        if pos > max_length * 0.6:  # 确保截断位置不会太前
            return text[:pos + 1]
    
    # 尝试在逗号、分号处截断
    for punct in ['，', '；', ',', ';']:
        pos = text[:max_length].rfind(punct)
        if pos > max_length * 0.7:
            return text[:pos + 1]
    
    # 尝试在空格处截断，避免截断中文字符
    pos = text[:max_length-3].rfind(' ')
    if pos > max_length * 0.7:
        return text[:pos] + "..."
    
    # 直接截断并添加省略号
    return text[:max_length-3] + "..."


def _generate_mr_notification_content(mr_review_entity: MergeRequestReviewEntity, mode: str):
    """生成MR通知内容"""
    # 基础信息
    score = _get_ai_score(mr_review_entity.review_result)
    server_url = get_env_with_default('UI_URL', 'http://localhost:5001')
    trigger_label = _get_trigger_type_label(mr_review_entity.trigger_type)
    
    # 获取MR ID和显示ID
    mr_id = mr_review_entity.mr_id
    if not mr_id and mr_review_entity.webhook_data:
        mr_id = mr_review_entity.webhook_data.get('object_attributes', {}).get('iid')
    display_id = mr_review_entity.webhook_data.get('object_attributes', {}).get('iid', mr_id) if mr_review_entity.webhook_data else mr_id
    
    detail_url = f"{server_url}/?review_type=mr&review_id={mr_id}"
    
    if mode == 'simplified':
        # 简化推送模式 - 优化布局
        ai_review = _get_simplified_review(mr_review_entity.review_result)
        score_emoji = _get_score_emoji(score)
        
        return f"""### 🔀 MR#{display_id} - {mr_review_entity.project_name}

**{mr_review_entity.source_branch}** → **{mr_review_entity.target_branch}**

👤 **{mr_review_entity.author}** | {score_emoji} **{score}分** | {trigger_label}

💡 **AI简评**: {ai_review}

🔗 [查看MR]({mr_review_entity.url}) | [详情页面]({detail_url})"""
    else:
        # 详细推送模式
        return f"""### 🔀 {mr_review_entity.project_name}: MR #{display_id} 详细审查报告

**分支**: {mr_review_entity.source_branch} → {mr_review_entity.target_branch}
**提交者**: {mr_review_entity.author}
**AI评分**: {score}分
**触发方式**: {trigger_label}

**审查详情**:
{mr_review_entity.review_result or '暂无详细审查结果'}

---
[查看MR详情]({mr_review_entity.url}) | [审查详情页面]({detail_url})"""


def _generate_push_notification_content(entity: PushReviewEntity, mode: str):
    """生成Push通知内容"""
    # 基础信息
    score = _get_ai_score(entity.review_result)
    server_url = get_env_with_default('UI_URL', 'http://localhost:5001')
    trigger_label = _get_trigger_type_label(entity.trigger_type)
    
    # 获取最新提交信息
    latest_commit = entity.commits[0] if entity.commits else {}
    commit_sha = latest_commit.get('id', 'unknown')
    commit_message = latest_commit.get('message', '').strip()
    author = latest_commit.get('author', 'Unknown')
    
    # 智能截断提交消息
    short_message = commit_message[:40] + ("..." if len(commit_message) > 40 else "")
    
    detail_url = f"{server_url}/?review_type=push&commit_sha={commit_sha}"
    
    if mode == 'simplified':
        # 简化推送模式 - 优化布局
        ai_review = _get_simplified_review(entity.review_result)
        score_emoji = _get_score_emoji(score)
        commits_count = len(entity.commits)
        
        return f"""### 🚀 Push - {entity.project_name}

📝 **{short_message}**

👤 **{author}** | {score_emoji} **{score}分** | 📊 **{commits_count}个提交** | {trigger_label}

💡 **AI简评**: {ai_review}

🔗 [查看代码]({latest_commit.get('url', '#')}) | [详情页面]({detail_url})"""
    else:
        # 详细推送模式
        commits_info = "\n".join([
            f"- **{commit.get('id', '')[:8]}**: {commit.get('message', '').strip()[:80]}..."
            for commit in entity.commits[:5]  # 最多显示5个提交
        ])
        if len(entity.commits) > 5:
            commits_info += f"\n- ... 还有 {len(entity.commits) - 5} 个提交"
            
        return f"""### 🚀 {entity.project_name}: Push事件详细审查报告

**最新提交**: {short_message}
**提交者**: {author}
**AI评分**: {score}分
**提交总数**: {len(entity.commits)}
**触发方式**: {trigger_label}

**提交列表**:
{commits_info}

**审查详情**:
{entity.review_result or '暂无详细审查结果'}

---
[查看代码]({latest_commit.get('url', '#')}) | [审查详情页面]({detail_url})"""


def _generate_svn_notification_content(entity: SvnReviewEntity, mode: str):
    """生成SVN通知内容"""
    # 基础信息
    score = _get_ai_score(entity.review_result)
    server_url = get_env_with_default('UI_URL', 'http://localhost:5001')
    trigger_label = _get_trigger_type_label(entity.trigger_type)
    
    # 获取最新提交信息
    latest_commit = entity.commits[0] if entity.commits else {}
    message = latest_commit.get('message', '').strip()
    author = latest_commit.get('author', entity.author)  # 备用作者名
    revision = entity.revision
    
    # 智能截断提交消息
    short_message = message[:40] + ("..." if len(message) > 40 else "") if message else "无提交消息"
    
    detail_url = f"{server_url}/?review_type=svn&revision={revision}"
    
    if mode == 'simplified':
        # 简化推送模式 - 优化布局
        ai_review = _get_simplified_review(entity.review_result)
        score_emoji = _get_score_emoji(score)
        
        return f"""### 📝 SVN r{revision} - {entity.project_name}

📝 **{short_message}**

👤 **{author}** | {score_emoji} **{score}分** | {trigger_label}

💡 **AI简评**: {ai_review}

🔗 [详情页面]({detail_url})"""
    else:
        # 详细推送模式
        return f"""### 📝 {entity.project_name}: SVN r{revision} 详细审查报告

**提交**: {short_message}
**提交者**: {author}
**AI评分**: {score}分
**版本号**: r{revision}
**触发方式**: {trigger_label}

**审查详情**:
{entity.review_result or '暂无详细审查结果'}

---
[审查详情页面]({detail_url})"""


def _get_trigger_type_label(trigger_type: str) -> str:
    """获取触发类型的中文标签"""
    trigger_labels = {
        "webhook": "🔄 实时触发",
        "manual": "👤 手动触发", 
        "scheduled": "⏰ 定时审查",
        "rerun": "🔄 重新审查"
    }
    return trigger_labels.get(trigger_type, "❓ 未知触发")


def _get_trigger_type_emoji(trigger_type: str) -> str:
    """获取触发类型的emoji"""
    trigger_emojis = {
        "webhook": "🔄",
        "manual": "👤",
        "scheduled": "⏰", 
        "rerun": "🔄"
    }
    return trigger_emojis.get(trigger_type, "❓")


# 定义事件处理函数
def on_merge_request_reviewed(mr_review_entity: MergeRequestReviewEntity):
    """处理MR审查事件"""
    # 获取推送模式配置
    notification_mode = get_env_with_default('NOTIFICATION_MODE', 'detailed')
    
    # 生成推送消息内容
    im_msg = _generate_mr_notification_content(mr_review_entity, notification_mode)
    
    notifier.send_notification(content=im_msg, msg_type='markdown', title='MR审查完成',
                               project_name=mr_review_entity.project_name, url_slug=mr_review_entity.url_slug,
                               webhook_data=mr_review_entity.webhook_data)

    # 记录到数据库
    ReviewService().insert_mr_review_log(mr_review_entity)


def on_push_reviewed(entity: PushReviewEntity):
    """处理Push审查事件"""
    # 获取推送模式配置
    notification_mode = get_env_with_default('NOTIFICATION_MODE', 'detailed')
    
    # 生成推送消息内容
    im_msg = _generate_push_notification_content(entity, notification_mode)

    notifier.send_notification(content=im_msg, msg_type='markdown',title=f"{entity.project_name} Push审查",
                               project_name=entity.project_name, url_slug=entity.url_slug,
                               webhook_data=entity.webhook_data)

    # 记录到数据库
    ReviewService().insert_push_review_log(entity)


def on_svn_reviewed(entity: SvnReviewEntity):
    """处理SVN审查事件"""
    # 获取推送模式配置
    notification_mode = get_env_with_default('NOTIFICATION_MODE', 'detailed')
    
    # 生成推送消息内容
    im_msg = _generate_svn_notification_content(entity, notification_mode)
    
    notifier.send_notification(
        content=im_msg, 
        msg_type='markdown',
        title=f"{entity.project_name} SVN审查",
        project_name=entity.project_name
    )

    # 记录到数据库（如果需要的话，可以扩展ReviewService支持SVN）
    # ReviewService().insert_svn_review_log(entity)


# 连接事件处理函数到事件信号
event_manager["merge_request_reviewed"].connect(on_merge_request_reviewed)
event_manager["push_reviewed"].connect(on_push_reviewed)
event_manager["svn_reviewed"].connect(on_svn_reviewed)
