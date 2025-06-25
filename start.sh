#!/bin/bash

# AI-CodeReview-Gitlab 智能启动脚本
# 支持多容器和单容器模式选择

set -e

# 全局变量
DOCKER_COMPOSE_CMD=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/start.log"

# 信号处理 - 防止意外退出
trap 'echo ""; log_warning "检测到中断信号，返回主菜单..."; echo ""' INT

# 写入日志文件
write_log() {
    local log_message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $log_message" >> "$LOG_FILE"
}

# Docker Compose 兼容函数
# 优先使用 docker compose，如果不可用则使用 docker-compose
docker_compose() {
    # 缓存检测结果以避免重复检查
    if [ -z "$DOCKER_COMPOSE_CMD" ]; then
        if docker compose version &> /dev/null; then
            DOCKER_COMPOSE_CMD="docker compose"
            log_info "使用 Docker Compose (新版本)"
        elif command -v docker-compose &> /dev/null; then
            DOCKER_COMPOSE_CMD="docker-compose"
            log_info "使用 docker-compose (经典版本)"
        else
            log_error "Docker Compose 未安装！请先安装 Docker Compose"
            write_log "ERROR: Docker Compose not found"
            return 1
        fi
    fi
    
    write_log "执行命令: $DOCKER_COMPOSE_CMD $*"
    
    # 执行命令并捕获错误
    if ! $DOCKER_COMPOSE_CMD "$@"; then
        local exit_code=$?
        log_error "Docker Compose 命令执行失败 (退出码: $exit_code)"
        write_log "ERROR: Docker Compose command failed with exit code $exit_code"
        return $exit_code
    fi
    
    return 0
}

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    local message="$1"
    echo -e "${BLUE}[INFO]${NC} $message"
    write_log "INFO: $message"
}

log_success() {
    local message="$1"
    echo -e "${GREEN}[SUCCESS]${NC} $message"
    write_log "SUCCESS: $message"
}

log_warning() {
    local message="$1"
    echo -e "${YELLOW}[WARNING]${NC} $message"
    write_log "WARNING: $message"
}

log_error() {
    local message="$1"
    echo -e "${RED}[ERROR]${NC} $message"
    write_log "ERROR: $message"
}

# 检查 Docker 和 Docker Compose
check_docker() {
    log_info "检查 Docker 环境..."
    
    if ! command -v docker &> /dev/null; then
        log_warning "Docker 未安装，准备安装..."
        if install_docker; then
            log_success "Docker 安装完成"
        else
            log_error "Docker 安装失败"
            return 1
        fi
    else
        log_info "Docker 已安装"
        
        # 检查 Docker 是否正在运行
        if ! docker info &> /dev/null; then
            log_error "Docker 未运行，请启动 Docker 服务"
            return 1
        fi
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_warning "Docker Compose 未安装，准备安装..."
        if install_docker_compose; then
            log_success "Docker Compose 安装完成"
        else
            log_error "Docker Compose 安装失败"
            return 1
        fi
    else
        log_info "Docker Compose 已安装"
    fi

    log_success "Docker 环境检查通过"
    return 0
}

# 安装 Docker
install_docker() {
    log_info "开始安装 Docker..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux 系统
        if command -v apt-get &> /dev/null; then
            # Ubuntu/Debian
            log_info "在 Ubuntu/Debian 系统上安装 Docker..."
            sudo apt-get update
            sudo apt-get install -y ca-certificates curl gnupg lsb-release
            
            # 添加 Docker 官方 GPG 密钥
            sudo mkdir -p /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            
            # 设置稳定版仓库
            echo \
                "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
                $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            # 安装 Docker Engine
            sudo apt-get update
            sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            
        elif command -v yum &> /dev/null; then
            # CentOS/RHEL
            log_info "在 CentOS/RHEL 系统上安装 Docker..."
            sudo yum install -y yum-utils
            sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        else
            log_error "不支持的 Linux 发行版，请手动安装 Docker"
            exit 1
        fi
        
        # 启动 Docker 服务
        sudo systemctl start docker
        sudo systemctl enable docker
        
        # 添加用户到 docker 组
        sudo usermod -aG docker $USER
        log_warning "请重新登录以使 Docker 权限生效，或使用 'newgrp docker' 命令"
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS 系统
        log_info "在 macOS 系统上安装 Docker..."
        if command -v brew &> /dev/null; then
            brew install --cask docker
            log_info "请启动 Docker Desktop 应用程序"
        else
            log_error "请先安装 Homebrew 或手动下载 Docker Desktop for Mac"
            exit 1
        fi
    else
        log_error "不支持的操作系统，请手动安装 Docker"
        exit 1
    fi
    
    log_success "Docker 安装完成"
}

# 安装 Docker Compose
install_docker_compose() {
    log_info "安装 Docker Compose..."
    
    # 获取最新版本号
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux 系统
        sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS 系统
        if command -v brew &> /dev/null; then
            brew install docker-compose
        else
            curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            chmod +x /usr/local/bin/docker-compose
        fi
    fi
    
    log_success "Docker Compose 安装完成"
}

# 下载配置文件
download_compose_files() {
    log_info "检查配置文件..."
    write_log "开始下载配置文件检查"
    
    BASE_URL="https://raw.githubusercontent.com/zhao-zg/AI-CODEREVIEW-GITLAB/main"
    local download_success=true
    local temp_dir="${SCRIPT_DIR}/.download_temp"
    
    # 创建临时目录
    mkdir -p "$temp_dir"
    
    # 下载多容器配置
    if [ ! -f "docker-compose.yml" ]; then
        log_info "下载多容器配置文件..."
        if curl -fsSL --connect-timeout 30 --max-time 300 "${BASE_URL}/docker-compose.yml" -o "${temp_dir}/docker-compose.yml"; then
            mv "${temp_dir}/docker-compose.yml" docker-compose.yml
            log_success "多容器配置文件下载完成"
        else
            log_error "多容器配置文件下载失败"
            download_success=false
        fi
    else
        log_info "多容器配置文件已存在"
    fi
    
    # 下载单容器配置
    if [ ! -f "docker-compose.single.yml" ]; then
        log_info "下载单容器配置文件..."
        if curl -fsSL --connect-timeout 30 --max-time 300 "${BASE_URL}/docker-compose.single.yml" -o "${temp_dir}/docker-compose.single.yml"; then
            mv "${temp_dir}/docker-compose.single.yml" docker-compose.single.yml
            log_success "单容器配置文件下载完成"
        else
            log_error "单容器配置文件下载失败"
            download_success=false
        fi
    else
        log_info "单容器配置文件已存在"
    fi
    
    # 下载 Dockerfile
    if [ ! -f "Dockerfile" ]; then
        log_info "下载 Dockerfile..."
        if curl -fsSL --connect-timeout 30 --max-time 300 "${BASE_URL}/Dockerfile" -o "${temp_dir}/Dockerfile"; then
            mv "${temp_dir}/Dockerfile" Dockerfile
            log_success "Dockerfile 下载完成"
        else
            log_warning "Dockerfile 下载失败，将使用预构建镜像"
        fi
    fi
    
    # 清理临时目录
    rm -rf "$temp_dir"
    
    if [ "$download_success" = true ]; then
        write_log "配置文件下载成功"
        return 0
    else
        log_warning "部分配置文件下载失败"
        write_log "配置文件下载部分失败"
        return 1
    fi
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    local required_dirs=("conf" "conf_runtime" "data" "log" "data/svn")
    local creation_success=true
    
    for dir in "${required_dirs[@]}"; do
        if mkdir -p "$dir" 2>/dev/null; then
            log_info "确保目录存在: $dir"
        else
            log_error "无法创建目录: $dir"
            creation_success=false
        fi
    done
    
    # 检查是否需要初始化运行时配置目录
    if [ ! -d "conf_runtime" ] || [ -z "$(ls -A conf_runtime 2>/dev/null)" ]; then
        log_info "运行时配置目录为空，准备从模板初始化..."
        
        # 如果有原始配置文件，先复制到运行时目录作为初始配置
        if [ -d "conf" ] && [ -n "$(ls -A conf 2>/dev/null)" ]; then
            log_info "从 conf/ 目录复制初始配置到 conf_runtime/..."
            if cp -r conf/* conf_runtime/ 2>/dev/null; then
                log_success "初始配置复制完成"
            else
                log_warning "初始配置复制失败"
                creation_success=false
            fi
        fi
    fi
    
    if [ "$creation_success" = true ]; then
        log_success "目录创建完成"
        return 0
    else
        log_warning "部分目录创建失败"
        return 1
    fi
}

# 显示部署模式选择菜单
show_deployment_menu() {
    echo ""
    echo "🚀 AI-CodeReview-Gitlab 部署模式选择"
    echo "=================================================="
    echo "1) 多容器模式 (推荐生产环境)"
    echo "   - 基础版：仅启动 API + UI 服务"
    echo "   - 完整版：启动 API + UI + Worker + Redis"
    echo ""
    echo "2) 单容器模式 (适合开发测试)"
    echo "   - 所有服务在一个容器中运行"
    echo "   - 可选启用 Redis 支持"
    echo ""
    echo "3) 停止所有服务"
    echo ""
    echo "4) 查看服务状态"
    echo ""
    echo "5) 查看服务日志"
    echo ""
    echo "6) 清理 Docker 资源"
    echo "   - 停止并删除所有相关容器"
    echo "   - 清理网络和卷资源"
    echo ""
    echo "7) 安装/更新环境"
    echo "   - 安装 Docker 和 Docker Compose"
    echo "   - 下载最新配置文件"
    echo ""
    echo "8) 下载配置文件"
    echo "   - 下载/更新 docker-compose.yml"
    echo "   - 下载/更新相关配置"
    echo ""
    echo "0) 退出"
    echo "=================================================="
}

# 多容器模式菜单
multi_container_menu() {
    while true; do
        echo ""
        echo "🔧 多容器模式选项："
        echo "1) 基础模式 (仅 API + UI)"
        echo "2) 完整模式 (API + UI + Worker + Redis)"
        echo "0) 返回主菜单"
        echo ""
        read -p "请选择 [1-2, 0]: " choice
        
        case $choice in
            1)
                log_info "启动多容器基础模式..."
                write_log "启动多容器基础模式"
                if docker_compose up -d; then
                    log_success "多容器基础模式启动成功"
                    write_log "多容器基础模式启动成功"
                    return 0
                else
                    log_error "多容器基础模式启动失败"
                    write_log "多容器基础模式启动失败"
                    echo ""
                    log_info "请尝试以下解决方案："
                    log_info "1. 检查 Docker 服务是否正常运行"
                    log_info "2. 检查配置文件是否存在且正确"
                    log_info "3. 查看详细日志进行诊断"
                    return 1
                fi
                ;;
            2)
                log_info "启动多容器完整模式..."
                write_log "启动多容器完整模式"
                if COMPOSE_PROFILES=worker docker_compose up -d; then
                    log_success "多容器完整模式启动成功"
                    write_log "多容器完整模式启动成功"
                    return 0
                else
                    log_error "多容器完整模式启动失败"
                    write_log "多容器完整模式启动失败"
                    echo ""
                    log_info "请尝试以下解决方案："
                    log_info "1. 检查 Docker 服务是否正常运行"
                    log_info "2. 检查配置文件是否存在且正确"
                    log_info "3. 查看详细日志进行诊断"
                    return 1
                fi
                ;;
            0)
                return 0
                ;;
            "")
                log_warning "请输入有效的选项"
                ;;
            *)
                log_warning "无效选择：'$choice'，请输入 1、2 或 0"
                ;;
        esac
    done
}

# 单容器模式菜单
single_container_menu() {
    while true; do
        echo ""
        echo "🔧 单容器模式选项："
        echo "1) 基础模式 (进程队列)"
        echo "2) Redis 模式 (包含 Redis 队列)"
        echo "0) 返回主菜单"
        echo ""
        read -p "请选择 [1-2, 0]: " choice
        
        case $choice in
            1)
                log_info "启动单容器基础模式..."
                write_log "启动单容器基础模式"
                if docker_compose -f docker-compose.single.yml up -d; then
                    log_success "单容器基础模式启动成功"
                    write_log "单容器基础模式启动成功"
                    return 0
                else
                    log_error "单容器基础模式启动失败"
                    write_log "单容器基础模式启动失败"
                    echo ""
                    log_info "请尝试以下解决方案："
                    log_info "1. 检查 Docker 服务是否正常运行"
                    log_info "2. 检查 docker-compose.single.yml 文件是否存在且正确"
                    log_info "3. 查看详细日志进行诊断"
                    return 1
                fi
                ;;
            2)
                log_info "启动单容器 Redis 模式..."
                write_log "启动单容器 Redis 模式"
                if COMPOSE_PROFILES=redis docker_compose -f docker-compose.single.yml up -d; then
                    log_success "单容器 Redis 模式启动成功"
                    write_log "单容器 Redis 模式启动成功"
                    return 0
                else
                    log_error "单容器 Redis 模式启动失败"
                    write_log "单容器 Redis 模式启动失败"
                    echo ""
                    log_info "请尝试以下解决方案："
                    log_info "1. 检查 Docker 服务是否正常运行"
                    log_info "2. 检查 docker-compose.single.yml 文件是否存在且正确"
                    log_info "3. 查看详细日志进行诊断"
                    return 1
                fi
                ;;
            0)
                return 0
                ;;
            "")
                log_warning "请输入有效的选项"
                ;;
            *)
                log_warning "无效选择：'$choice'，请输入 1、2 或 0"
                ;;
        esac
    done
}

# 停止所有服务
stop_all_services() {
    log_info "停止所有服务..."
    local stopped_any=false
    local stop_errors=0
    
    # 尝试停止多容器服务
    if docker_compose ps -q 2>/dev/null | grep -q .; then
        log_info "停止多容器服务..."
        if docker_compose down --remove-orphans; then
            log_success "多容器服务已停止"
            stopped_any=true
        else
            log_warning "停止多容器服务时出现问题"
            ((stop_errors++))
        fi
    fi
    
    # 尝试停止单容器服务
    if docker_compose -f docker-compose.single.yml ps -q 2>/dev/null | grep -q .; then
        log_info "停止单容器服务..."
        if docker_compose -f docker-compose.single.yml down --remove-orphans; then
            log_success "单容器服务已停止"
            stopped_any=true
        else
            log_warning "停止单容器服务时出现问题"
            ((stop_errors++))
        fi
    fi
    
    # 清理可能存在的网络冲突（更安全的方式）
    cleanup_networks_safe
    
    if [ "$stopped_any" = true ]; then
        if [ $stop_errors -eq 0 ]; then
            log_success "所有服务已停止"
        else
            log_warning "服务已停止，但存在 $stop_errors 个警告"
        fi
    else
        log_info "没有发现运行中的服务"
    fi
    
    return 0
}

# 安全清理网络函数
cleanup_networks_safe() {
    log_info "安全清理网络资源..."
    
    # 获取所有包含 ai-codereview 的网络，但只清理未被使用的
    local networks=$(docker network ls --format "{{.Name}}" | grep -E "(ai-codereview|aicodereview)" 2>/dev/null || true)
    
    if [ -n "$networks" ]; then
        echo "$networks" | while read -r network; do
            if [ -n "$network" ]; then
                # 检查网络是否正在被使用
                local network_in_use=$(docker network inspect "$network" --format '{{len .Containers}}' 2>/dev/null || echo "0")
                
                if [ "$network_in_use" = "0" ]; then
                    log_info "删除未使用的网络: $network"
                    if docker network rm "$network" 2>/dev/null; then
                        log_success "网络 $network 已删除"
                    else
                        log_warning "无法删除网络 $network"
                    fi
                else
                    log_info "网络 $network 正在使用中，跳过删除"
                fi
            fi
        done
    else
        log_info "没有发现相关网络需要清理"
    fi
}

# 清理 Docker 网络和资源
cleanup_docker_resources() {
    log_info "清理 Docker 资源..."
    
    # 停止所有相关容器
    log_info "停止 AI-CodeReview 相关容器..."
    docker stop $(docker ps -q --filter "name=ai-codereview") 2>/dev/null || true
    
    # 删除所有相关容器
    log_info "删除 AI-CodeReview 相关容器..."
    docker rm $(docker ps -aq --filter "name=ai-codereview") 2>/dev/null || true
    
    # 删除网络
    log_info "删除网络..."
    docker network rm ai-codereview-network 2>/dev/null || true
    
    # 删除未使用的卷
    log_info "清理未使用的卷..."
    docker volume prune -f 2>/dev/null || true
    
    # 清理未使用的网络
    log_info "清理未使用的网络..."
    docker network prune -f 2>/dev/null || true
    
    log_success "Docker 资源清理完成"
}

# 查看服务状态
show_service_status() {
    echo ""
    log_info "=== 多容器服务状态 ==="
    docker_compose ps 2>/dev/null || echo "无多容器服务运行"
    
    echo ""
    log_info "=== 单容器服务状态 ==="
    docker_compose -f docker-compose.single.yml ps 2>/dev/null || echo "无单容器服务运行"
    
    echo ""
    log_info "=== Docker 容器状态 ==="
    docker ps --filter "name=ai-codereview" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

# 查看服务日志
show_service_logs() {
    while true; do
        echo ""
        echo "📋 选择要查看的日志："
        echo "1) 多容器服务日志"
        echo "2) 单容器服务日志"
        echo "3) 特定容器日志"
        echo "0) 返回主菜单"
        echo ""
        read -p "请选择 [1-3, 0]: " choice
        
        case $choice in
            1)
                log_info "显示多容器服务日志..."
                if docker_compose ps -q 2>/dev/null | grep -q .; then
                    docker_compose logs -f --tail=100
                else
                    log_warning "没有运行中的多容器服务"
                fi
                ;;
            2)
                log_info "显示单容器服务日志..."
                if docker_compose -f docker-compose.single.yml ps -q 2>/dev/null | grep -q .; then
                    docker_compose -f docker-compose.single.yml logs -f --tail=100
                else
                    log_warning "没有运行中的单容器服务"
                fi
                ;;  
            3)
                echo ""
                echo "可用容器："
                local containers=$(docker ps --filter "name=ai-codereview" --format "{{.Names}}")
                if [ -n "$containers" ]; then
                    echo "$containers"
                    echo ""
                    read -p "请输入容器名称: " container_name
                    if [ -n "$container_name" ]; then
                        if docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
                            docker logs -f --tail=100 "$container_name"
                        else
                            log_warning "容器 '$container_name' 不存在或未运行"
                        fi
                    else
                        log_warning "容器名称不能为空"
                    fi
                else
                    log_warning "没有发现运行中的 AI-CodeReview 容器"
                fi
                ;;
            0)
                return 0
                ;;
            "")
                log_warning "请输入有效的选项"
                ;;
            *)
                log_warning "无效选择：'$choice'，请输入 1-3 或 0"
                ;;
        esac
        
        # 日志查看结束后提示用户
        echo ""
        read -p "日志查看结束，按回车键返回日志菜单..." dummy
    done
}

# 检查服务健康状态
check_service_health() {
    log_info "检查服务健康状态..."
    local all_healthy=true
    local max_retries=5
    local retry_interval=6
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 5
    
    # 检查 API 服务
    log_info "检查 API 服务健康状态..."
    local api_healthy=false
    for ((i=1; i<=max_retries; i++)); do
        log_info "API 健康检查尝试 $i/$max_retries..."
        
        if timeout 10 curl -s http://localhost:5001/health >/dev/null 2>&1; then
            log_success "API 服务 (端口 5001) 运行正常"
            api_healthy=true
            break
        elif timeout 5 curl -s http://localhost:5001 >/dev/null 2>&1; then
            log_success "API 服务 (端口 5001) 响应正常 (health endpoint 不可用)"
            api_healthy=true
            break
        else
            # 检查端口是否被占用
            if netstat -tuln 2>/dev/null | grep -q ":5001 " || ss -tuln 2>/dev/null | grep -q ":5001 "; then
                log_warning "API 服务 (端口 5001) 端口已开启，但服务未完全就绪"
                if [ $i -eq $max_retries ]; then
                    log_warning "API 服务启动超时，但端口已占用"
                fi
            else
                log_warning "API 服务 (端口 5001) 可能未启动"
                if [ $i -eq $max_retries ]; then
                    all_healthy=false
                fi
            fi
        fi
        
        if [ $i -lt $max_retries ]; then
            log_info "等待 ${retry_interval}s 后重试..."
            sleep $retry_interval
        fi
    done
    
    # 检查 UI 服务
    log_info "检查 UI 服务健康状态..."
    local ui_healthy=false
    for ((i=1; i<=max_retries; i++)); do
        log_info "UI 健康检查尝试 $i/$max_retries..."
        
        if timeout 10 curl -s http://localhost:5002 >/dev/null 2>&1; then
            log_success "UI 服务 (端口 5002) 运行正常"
            ui_healthy=true
            break
        else
            # 检查端口是否被占用
            if netstat -tuln 2>/dev/null | grep -q ":5002 " || ss -tuln 2>/dev/null | grep -q ":5002 "; then
                log_warning "UI 服务 (端口 5002) 端口已开启，可能仍在启动中"
                if [ $i -eq $max_retries ]; then
                    log_warning "UI 服务启动超时，但端口已占用"
                    ui_healthy=true  # Streamlit 需要更长时间启动，但端口占用说明服务正在运行
                fi
            else
                log_warning "UI 服务 (端口 5002) 可能未启动"
                if [ $i -eq $max_retries ]; then
                    all_healthy=false
                fi
            fi
        fi
        
        if [ $i -lt $max_retries ] && [ "$ui_healthy" = false ]; then
            log_info "等待 ${retry_interval}s 后重试..."
            sleep $retry_interval
        fi
    done
    
    # 汇总健康检查结果
    if [ "$api_healthy" = true ] && [ "$ui_healthy" = true ]; then
        log_success "所有服务健康检查通过"
        echo ""
        log_info "🌐 服务访问地址："
        log_info "   API 服务: http://localhost:5001"
        log_info "   UI 界面:  http://localhost:5002"
        echo ""
        log_info "💡 提示: 如果 UI 界面加载较慢，请等待 Streamlit 完全启动"
    elif [ "$api_healthy" = true ] || [ "$ui_healthy" = true ]; then
        log_warning "部分服务健康检查通过"
        echo ""
        if [ "$api_healthy" = true ]; then
            log_info "✅ API 服务: http://localhost:5001"
        fi
        if [ "$ui_healthy" = true ]; then
            log_info "✅ UI 界面:  http://localhost:5002"
        fi
        echo ""
        log_warning "请检查日志以诊断未启动的服务"
    else
        log_warning "服务健康检查未完全通过，请查看日志进行诊断"
        echo ""
        log_info "🔧 诊断建议:"
        log_info "   1. 检查 Docker 容器状态: docker ps"
        log_info "   2. 查看服务日志: 选择菜单项 '5) 查看服务日志'"
        log_info "   3. 检查端口占用: netstat -tuln | grep :500"
    fi
    
    return 0
}

# 预检查必要配置文件
preflight_check() {
    log_info "执行启动前检查..."
    local check_passed=true
    
    # 检查必要的配置文件
    local required_files=("docker-compose.yml" "docker-compose.single.yml")
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_warning "缺少配置文件: $file"
            check_passed=false
        else
            log_info "配置文件存在: $file"
        fi
    done
    
    # 检查 Docker 是否可用
    if ! docker info &> /dev/null; then
        log_error "Docker 不可用，请确保 Docker 服务正在运行"
        check_passed=false
    fi
    
    # 检查端口是否被占用
    check_port_conflicts
    local port_check=$?
    if [ $port_check -ne 0 ]; then
        check_passed=false
    fi
    
    if [ "$check_passed" = true ]; then
        log_success "启动前检查通过"
        return 0
    else
        log_warning "启动前检查发现问题，但仍可尝试启动"
        return 1
    fi
}

# 检查端口冲突
check_port_conflicts() {
    log_info "检查端口占用情况..."
    local ports_in_use=()
    
    # 检查主要端口
    local check_ports=(5001 5002 6379)
    for port in "${check_ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":${port} " || ss -tuln 2>/dev/null | grep -q ":${port} "; then
            ports_in_use+=("$port")
            log_warning "端口 $port 已被占用"
        fi
    done
    
    if [ ${#ports_in_use[@]} -eq 0 ]; then
        log_info "所有必要端口都可用"
        return 0
    else
        log_warning "发现 ${#ports_in_use[@]} 个端口被占用: ${ports_in_use[*]}"
        log_info "如果这些端口被 AI-CodeReview 的其他实例占用，请先停止它们"
        return 1
    fi
}

# 初始化启动日志
init_startup_log() {
    echo "================================" >> "$LOG_FILE"
    echo "AI-CodeReview 启动日志" >> "$LOG_FILE"
    echo "启动时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
    echo "脚本版本: 2.1" >> "$LOG_FILE"
    echo "脚本路径: $SCRIPT_DIR" >> "$LOG_FILE"
    echo "================================" >> "$LOG_FILE"
}

# 主函数
main() {
    # 初始化启动日志
    init_startup_log
    
    echo ""
    echo "🎯 AI-CodeReview-Gitlab 智能启动助手"
    echo "版本: 2.1 | 支持多容器/单容器部署"
    echo ""

    # 执行启动前检查
    preflight_check

    # 检查环境和下载配置文件
    if ! download_compose_files; then
        log_warning "配置文件下载失败，但将尝试继续运行"
    fi
    
    if ! check_docker; then
        log_error "Docker 环境检查失败，无法继续"
        exit 1
    fi
    
    if ! create_directories; then
        log_warning "目录创建存在问题，但将尝试继续运行"
    fi

    while true; do
        show_deployment_menu
        read -p "请选择操作 [0-8]: " choice
        
        # 处理空输入
        if [ -z "$choice" ]; then
            log_warning "请输入有效的选项"
            continue
        fi

        case $choice in
            1)
                multi_container_menu
                local exit_code=$?
                if [ $exit_code -eq 0 ]; then
                    check_service_health
                fi
                ;;
            2)
                single_container_menu  
                local exit_code=$?
                if [ $exit_code -eq 0 ]; then
                    check_service_health
                fi
                ;;
            3)
                stop_all_services
                ;;
            4)
                show_service_status
                ;;
            5)
                show_service_logs
                ;;
            6)
                cleanup_docker_resources
                ;;
            7)
                log_info "开始安装/更新环境..."
                if check_docker; then
                    log_success "Docker 环境检查通过"
                else
                    log_warning "Docker 环境检查失败"
                fi
                download_compose_files
                log_success "环境检查/更新完成"
                ;;
            8)
                log_info "开始下载配置文件..."
                download_compose_files
                ;;
            0)
                log_info "感谢使用 AI-CodeReview-Gitlab!"
                write_log "用户退出程序"
                exit 0
                ;;
            "")
                log_warning "请输入有效的选项"
                ;;
            *)
                log_warning "无效选择：'$choice'，请输入 0-8 之间的数字"
                echo "提示: 输入 0 退出程序"
                ;;
        esac

        echo ""
        read -p "按回车键继续..." dummy
    done
}

# 脚本入口
main "$@"
