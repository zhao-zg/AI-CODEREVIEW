#!/bin/bash

# AI-CodeReview 智能启动脚本
# 单容器架构 - API、Worker、UI 三合一

# 注意：不使用 set -e 以允许更灵活的错误处理

# 全局变量
DOCKER_COMPOSE_CMD=""
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/start.log"

# 信号处理 - 防止意外退出
trap 'echo ""; echo "检测到中断信号，返回主菜单..."; echo ""' INT

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
    
    # 如果设置了自定义 compose 文件，使用 -f 参数
    local compose_args=""
    if [ -n "$CUSTOM_COMPOSE_FILE" ]; then
        compose_args="-f $CUSTOM_COMPOSE_FILE"
    fi
    
    write_log "执行命令: $DOCKER_COMPOSE_CMD $compose_args $*"
    
    # 执行命令并捕获错误
    if ! $DOCKER_COMPOSE_CMD $compose_args "$@"; then
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
    
    local required_dirs="conf data log data/svn"
    local creation_success=true
    
    for dir in $required_dirs; do
        if mkdir -p "$dir" 2>/dev/null; then
            log_info "确保目录存在: $dir"
        else
            log_error "无法创建目录: $dir"
            creation_success=false
        fi
    done
    
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
    echo "🚀 AI-CodeReview 部署管理"
    echo "=================================================="
    echo "1) 启动服务 (单容器模式)"
    echo "   - API + Worker + UI 三合一"
    echo "   - 支持内存队列和 Redis 队列"
    echo ""
    echo "2) 停止服务"
    echo ""
    echo "3) 查看服务状态"
    echo ""
    echo "4) 查看服务日志"
    echo ""
    echo "5) 重启服务"
    echo ""
    echo "6) 清理 Docker 资源"
    echo "   - 停止并删除所有相关容器"
    echo "   - 清理网络和卷资源"
    echo ""
    echo "7) 安装/更新环境"
    echo "   - 安装 Docker 和 Docker Compose"
    echo "   - 下载最新配置文件"
    echo ""
    echo "8) 拉取最新镜像"
    echo "   - 拉取最新的 Docker 镜像"
    echo "   - 不启动服务"
    echo ""
    echo "9) 下载配置文件"
    echo "   - 下载/更新 docker-compose.yml"
    echo "   - 下载/更新相关配置"
    echo ""
    echo "0) 退出"
    echo "=================================================="
}

# 启动服务菜单
start_service_menu() {
    while true; do
        echo ""
        echo "🔧 启动服务选项："
        echo "1) 基础模式 (内存队列) - 使用默认配置"
        echo "2) Redis 模式 (Redis 队列) - 使用默认配置"
        echo "3) 基础模式 (内存队列) - 自定义端口和容器名"
        echo "4) Redis 模式 (Redis 队列) - 自定义端口和容器名"
        echo "0) 返回主菜单"
        echo ""
        read -p "请选择 [1-4, 0]: " choice
        
        case $choice in
            1)
                log_info "启动基础模式 (内存队列) - 默认配置..."
                write_log "启动基础模式 - 默认配置"
                
                # 拉取最新镜像
                log_info "拉取最新 Docker 镜像..."
                if docker_compose pull; then
                    log_success "镜像拉取完成"
                else
                    log_warning "镜像拉取失败，将使用本地缓存镜像"
                fi
                
                if docker_compose up -d; then
                    log_success "基础模式启动成功"
                    write_log "基础模式启动成功"
                    echo ""
                    log_info "服务地址："
                    log_info "- API: http://localhost:5001"
                    log_info "- UI: http://localhost:5002"
                    return 0
                else
                    log_error "基础模式启动失败"
                    write_log "基础模式启动失败"
                    echo ""
                    log_info "请尝试以下解决方案："
                    log_info "1. 检查 Docker 服务是否正常运行"
                    log_info "2. 检查 docker-compose.yml 文件是否存在且正确"
                    log_info "3. 查看详细日志进行诊断"
                    return 1
                fi
                ;;
            2)
                log_info "启动 Redis 模式 - 默认配置..."
                write_log "启动 Redis 模式 - 默认配置"
                
                # 设置使用 single compose 文件
                export CUSTOM_COMPOSE_FILE="docker-compose.single.yml"
                
                # 拉取最新镜像
                log_info "拉取最新 Docker 镜像..."
                if COMPOSE_PROFILES=redis docker_compose pull; then
                    log_success "镜像拉取完成"
                else
                    log_warning "镜像拉取失败，将使用本地缓存镜像"
                fi
                
                if COMPOSE_PROFILES=redis docker_compose up -d; then
                    log_success "Redis 模式启动成功"
                    write_log "Redis 模式启动成功"
                    echo ""
                    log_info "服务地址："
                    log_info "- API: http://localhost:5001"
                    log_info "- UI: http://localhost:5002"
                    log_info "- Redis: localhost:6379"
                    return 0
                else
                    log_error "Redis 模式启动失败"
                    write_log "Redis 模式启动失败"
                    echo ""
                    log_info "请尝试以下解决方案："
                    log_info "1. 检查 Docker 服务是否正常运行"
                    log_info "2. 检查 docker-compose.single.yml 文件是否存在且正确"
                    log_info "3. 查看详细日志进行诊断"
                    return 1
                fi
                ;;
            3)
                log_info "启动基础模式 (内存队列) - 自定义端口和容器名..."
                write_log "启动基础模式 - 自定义端口和容器名"
                
                # 仅配置端口参数
                configure_port_parameters

                # 配置容器名
                while true; do
                    read -p "请输入容器名 (默认: ai-codereview，直接回车使用默认): " container_name
                    if [ -z "$container_name" ]; then
                        container_name="ai-codereview"
                        break
                    elif [[ "$container_name" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]]; then
                        break
                    else
                        log_warning "容器名只能包含字母、数字、点号、下划线和连字符，且必须以字母或数字开头"
                    fi
                done
                
                # 设置环境变量
                export AI_CODEREVIEW_API_PORT="${CUSTOM_API_PORT:-5001}"
                export AI_CODEREVIEW_UI_PORT="${CUSTOM_UI_PORT:-5002}"
                export AI_CODEREVIEW_CONTAINER_NAME="$container_name"
                
                # 拉取最新镜像
                log_info "拉取最新 Docker 镜像..."
                if docker_compose pull; then
                    log_success "镜像拉取完成"
                else
                    log_warning "镜像拉取失败，将使用本地缓存镜像"
                fi
                
                if docker_compose up -d; then
                    log_success "基础模式启动成功"
                    write_log "基础模式启动成功 - 自定义端口和容器名"
                    echo ""
                    log_info "服务地址："
                    log_info "- API: http://localhost:${CUSTOM_API_PORT:-5001}"
                    log_info "- UI: http://localhost:${CUSTOM_UI_PORT:-5002}"
                    log_info "- 容器名: ${AI_CODEREVIEW_CONTAINER_NAME}"
                    return 0
                else
                    log_error "基础模式启动失败"
                    write_log "基础模式启动失败 - 自定义端口和容器名"
                    echo ""
                    log_info "请尝试以下解决方案："
                    log_info "1. 检查 Docker 服务是否正常运行"
                    log_info "2. 检查端口是否被占用"
                    log_info "3. 检查容器名是否冲突"
                    log_info "4. 查看详细日志进行诊断"
                    return 1
                fi
                ;;
            4)
                log_info "启动 Redis 模式 - 自定义配置..."
                write_log "启动 Redis 模式 - 自定义配置"
                
                # 设置使用 single compose 文件
                export CUSTOM_COMPOSE_FILE="docker-compose.single.yml"
                
                # 配置服务参数
                configure_service_parameters
                
                # 设置环境变量
                export AI_CODEREVIEW_CONTAINER_NAME="${CUSTOM_CONTAINER_NAME:-ai-codereview}"
                export AI_CODEREVIEW_API_PORT="${CUSTOM_API_PORT:-5001}"
                export AI_CODEREVIEW_UI_PORT="${CUSTOM_UI_PORT:-5002}"
                export AI_CODEREVIEW_REDIS_CONTAINER_NAME="${CUSTOM_REDIS_CONTAINER_NAME:-ai-codereview-redis}"
                
                # 拉取最新镜像
                log_info "拉取最新 Docker 镜像..."
                if COMPOSE_PROFILES=redis docker_compose pull; then
                    log_success "镜像拉取完成"
                else
                    log_warning "镜像拉取失败，将使用本地缓存镜像"
                fi
                
                if COMPOSE_PROFILES=redis docker_compose up -d; then
                    log_success "Redis 模式启动成功"
                    write_log "Redis 模式启动成功 - 自定义配置"
                    echo ""
                    log_info "服务地址："
                    log_info "- API: http://localhost:${CUSTOM_API_PORT:-5001}"
                    log_info "- UI: http://localhost:${CUSTOM_UI_PORT:-5002}"
                    log_info "- Redis: localhost:6379"
                    log_info "- 容器名: ${CUSTOM_CONTAINER_NAME:-ai-codereview}"
                    log_info "- Redis 容器名: ${CUSTOM_REDIS_CONTAINER_NAME:-ai-codereview-redis}"
                    return 0
                else
                    log_error "Redis 模式启动失败"
                    write_log "Redis 模式启动失败 - 自定义配置"
                    echo ""
                    log_info "请尝试以下解决方案："
                    log_info "1. 检查 Docker 服务是否正常运行"
                    log_info "2. 检查端口是否被占用"
                    log_info "3. 检查容器名是否冲突"
                    log_info "4. 查看详细日志进行诊断"
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
                log_warning "无效选择：'$choice'，请输入 1-4 或 0"
                ;;
        esac
    done
}

# 重启服务
restart_service() {
    log_info "重启服务..."
    write_log "重启服务"
    
    echo ""
    echo "🔄 重启服务选项："
    echo "1) 停止所有服务并重新选择启动模式"
    echo "2) 快速重启 (使用默认配置)"
    echo "0) 取消"
    echo ""
    read -p "请选择 [1-2, 0]: " restart_choice
    
    case $restart_choice in
        1)
            log_info "停止所有服务..."
            # 停止可能的服务
            docker_compose down --remove-orphans 2>/dev/null || true
            CUSTOM_COMPOSE_FILE="docker-compose.single.yml" docker_compose down --remove-orphans 2>/dev/null || true
            
            log_info "请重新选择启动模式..."
            start_service_menu
            ;;
        2)
            log_info "快速重启服务..."
            # 停止服务
            docker_compose down --remove-orphans
            
            # 拉取最新镜像
            log_info "拉取最新 Docker 镜像..."
            if docker_compose pull; then
                log_success "镜像拉取完成"
            else
                log_warning "镜像拉取失败，将使用本地缓存镜像"
            fi
            
            # 启动服务
            if docker_compose up -d; then
                log_success "服务重启成功"
                write_log "服务重启成功"
                echo ""
                log_info "服务地址："
                log_info "- API: http://localhost:5001"
                log_info "- UI: http://localhost:5002"
                check_service_health
            else
                log_error "服务重启失败"
                write_log "服务重启失败"
            fi
            ;;
        0)
            log_info "取消重启"
            return 0
            ;;
        "")
            log_warning "请输入有效的选项"
            restart_service
            ;;
        *)
            log_warning "无效选择：'$restart_choice'，请输入 1、2 或 0"
            restart_service
            ;;
    esac
}

# 停止服务
stop_service() {
    log_info "停止服务..."
    write_log "停止服务"
    
    if docker_compose down --remove-orphans; then
        log_success "服务停止成功"
        write_log "服务停止成功"
    else
        log_error "服务停止失败"
        write_log "服务停止失败"
    fi
}

# 查看服务状态
show_service_status() {
    echo ""
    log_info "=== AI-CodeReview 服务状态 ==="
    docker_compose ps 2>/dev/null || echo "无服务运行"
    echo ""
    log_info "=== Docker 容器状态 ==="
    docker ps --filter "name=${AI_CODEREVIEW_CONTAINER_NAME:-ai-codereview}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

# 查看服务日志
show_service_logs() {
    echo ""
    log_info "=== AI-CodeReview 服务日志 ==="
    # 跟随最新日志，显示最后100行
    docker_compose logs --tail 100 -f
}

# 配置服务参数（端口和容器名）
configure_service_parameters() {
    log_info "配置服务参数..."
    echo ""
    echo "🔧 服务参数配置"
    echo "=================================================="
    echo "当前默认配置："
    echo "- API 端口: 5001"
    echo "- UI 端口: 5002"
    echo "- 主容器名: ai-codereview"
    echo "- Redis 容器名: ai-codereview-redis"
    echo "=================================================="
    echo ""
    
    # 配置 API 端口
    while true; do
        read -p "请输入 API 端口 (默认: 5001，直接回车使用默认): " api_port
        if [ -z "$api_port" ]; then
            api_port="5001"
            break
        elif [[ "$api_port" =~ ^[0-9]+$ ]] && [ "$api_port" -ge 1 ] && [ "$api_port" -le 65535 ]; then
            # 检查端口是否被占用
            if netstat -an 2>/dev/null | grep -q ":$api_port " || ss -tuln 2>/dev/null | grep -q ":$api_port "; then
                log_warning "端口 $api_port 可能已被占用，请选择其他端口或确认"
                read -p "是否继续使用端口 $api_port？(y/N): " confirm
                if [[ "$confirm" =~ ^[yY]$ ]]; then
                    break
                fi
            else
                break
            fi
        else
            log_warning "请输入有效的端口号 (1-65535)"
        fi
    done
    
    # 配置 UI 端口
    while true; do
        read -p "请输入 UI 端口 (默认: 5002，直接回车使用默认): " ui_port
        if [ -z "$ui_port" ]; then
            ui_port="5002"
            break
        elif [[ "$ui_port" =~ ^[0-9]+$ ]] && [ "$ui_port" -ge 1 ] && [ "$ui_port" -le 65535 ]; then
            if [ "$ui_port" = "$api_port" ]; then
                log_warning "UI 端口不能与 API 端口相同"
                continue
            fi
            # 检查端口是否被占用
            if netstat -an 2>/dev/null | grep -q ":$ui_port " || ss -tuln 2>/dev/null | grep -q ":$ui_port "; then
                log_warning "端口 $ui_port 可能已被占用，请选择其他端口或确认"
                read -p "是否继续使用端口 $ui_port？(y/N): " confirm
                if [[ "$confirm" =~ ^[yY]$ ]]; then
                    break
                fi
            else
                break
            fi
        else
            log_warning "请输入有效的端口号 (1-65535)"
        fi
    done
    
    # 配置容器名
    while true; do
        read -p "请输入主容器名 (默认: ai-codereview，直接回车使用默认): " container_name
        if [ -z "$container_name" ]; then
            container_name="ai-codereview"
            break
        elif [[ "$container_name" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]]; then
            # 检查容器名是否已存在
            if docker ps -a --format "{{.Names}}" | grep -q "^${container_name}$"; then
                log_warning "容器名 '$container_name' 已存在"
                read -p "是否停止并移除现有容器？(y/N): " confirm
                if [[ "$confirm" =~ ^[yY]$ ]]; then
                    log_info "停止并移除现有容器 '$container_name'"
                    docker stop "$container_name" 2>/dev/null || true
                    docker rm "$container_name" 2>/dev/null || true
                    break
                fi
            else
                break
            fi
        else
            log_warning "容器名只能包含字母、数字、点号、下划线和连字符，且必须以字母或数字开头"
        fi
    done
    
    # 配置 Redis 容器名
    while true; do
        read -p "请输入 Redis 容器名 (默认: ai-codereview-redis，直接回车使用默认): " redis_container_name
        if [ -z "$redis_container_name" ]; then
            redis_container_name="ai-codereview-redis"
            break
        elif [[ "$redis_container_name" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]]; then
            if [ "$redis_container_name" = "$container_name" ]; then
                log_warning "Redis 容器名不能与主容器名相同"
                continue
            fi
            # 检查容器名是否已存在
            if docker ps -a --format "{{.Names}}" | grep -q "^${redis_container_name}$"; then
                log_warning "容器名 '$redis_container_name' 已存在"
                read -p "是否停止并移除现有容器？(y/N): " confirm
                if [[ "$confirm" =~ ^[yY]$ ]]; then
                    log_info "停止并移除现有容器 '$redis_container_name'"
                    docker stop "$redis_container_name" 2>/dev/null || true
                    docker rm "$redis_container_name" 2>/dev/null || true
                    break
                fi
            else
                break
            fi
        else
            log_warning "容器名只能包含字母、数字、点号、下划线和连字符，且必须以字母或数字开头"
        fi
    done
    
    # 确认配置
    echo ""
    echo "📋 配置确认："
    echo "- API 端口: $api_port"
    echo "- UI 端口: $ui_port"
    echo "- 主容器名: $container_name"
    echo "- Redis 容器名: $redis_container_name"
    echo ""
    read -p "确认使用以上配置？(Y/n): " confirm
    if [[ "$confirm" =~ ^[nN]$ ]]; then
        log_info "重新配置参数..."
        configure_service_parameters
        return
    fi
    
    # 导出环境变量供后续使用
    export CUSTOM_API_PORT="$api_port"
    export CUSTOM_UI_PORT="$ui_port"
    export CUSTOM_CONTAINER_NAME="$container_name"
    export CUSTOM_REDIS_CONTAINER_NAME="$redis_container_name"
    
    log_success "服务参数配置完成"
    write_log "配置参数: API端口=$api_port, UI端口=$ui_port, 主容器名=$container_name, Redis容器名=$redis_container_name"
}

# 配置端口参数（仅基础模式自定义配置使用）
configure_port_parameters() {
    log_info "配置端口参数..."
    echo ""
    echo "🔧 端口参数配置"
    echo "=================================================="
    echo "当前默认端口： API=5001, UI=5002"
    echo "=================================================="
    echo ""
    # 配置 API 端口
    while true; do
        read -p "请输入 API 端口 (默认: 5001，直接回车使用默认): " api_port
        if [ -z "$api_port" ]; then
            api_port="5001"
            break
        elif [[ "$api_port" =~ ^[0-9]+$ ]] && [ "$api_port" -ge 1 ] && [ "$api_port" -le 65535 ]; then
            # 检查端口是否被占用
            if netstat -an 2>/dev/null | grep -q ":$api_port " || ss -tuln 2>/dev/null | grep -q ":$api_port "; then
                log_warning "端口 $api_port 可能已被占用，请选择其他端口或确认"
                read -p "是否继续使用端口 $api_port？(y/N): " confirm
                if [[ "$confirm" =~ ^[yY]$ ]]; then
                    break
                fi
            else
                break
            fi
        else
            log_warning "请输入有效的端口号 (1-65535)"
        fi
    done
    
    # 配置 UI 端口
    while true; do
        read -p "请输入 UI 端口 (默认: 5002，直接回车使用默认): " ui_port
        if [ -z "$ui_port" ]; then
            ui_port="5002"
            break
        elif [[ "$ui_port" =~ ^[0-9]+$ ]] && [ "$ui_port" -ge 1 ] && [ "$ui_port" -le 65535 ]; then
            if [ "$ui_port" = "$api_port" ]; then
                log_warning "UI 端口不能与 API 端口相同"
                continue
            fi
            # 检查端口是否被占用
            if netstat -an 2>/dev/null | grep -q ":$ui_port " || ss -tuln 2>/dev/null | grep -q ":$ui_port "; then
                log_warning "端口 $ui_port 可能已被占用，请选择其他端口或确认"
                read -p "是否继续使用端口 $ui_port？(y/N): " confirm
                if [[ "$confirm" =~ ^[yY]$ ]]; then
                    break
                fi
            else
                break
            fi
        else
            log_warning "请输入有效的端口号 (1-65535)"
        fi
    done
    
    # 导出环境变量
    export CUSTOM_API_PORT="$api_port"
    export CUSTOM_UI_PORT="$ui_port"
    log_success "端口参数配置完成: API=$api_port, UI=$ui_port"
    write_log "配置端口: API端口=$api_port, UI端口=$ui_port"
}

# 下载并启动服务
download_and_start_service() {
    log_info "下载并启动服务..."
    
    # 下载配置文件
    if ! download_compose_files; then
        log_error "配置文件下载失败，无法启动服务"
        return 1
    fi
    
    # 检查 Docker 环境
    if ! check_docker; then
        log_warning "Docker 环境检查失败，某些功能可能不可用"
        log_info "您仍可以使用菜单选项 7 来安装 Docker 环境"
    fi
    
    # 创建必要目录
    if ! create_directories; then
        log_warning "目录创建存在问题，但将尝试继续运行"
    fi
    
    # 配置服务参数
    configure_service_parameters
    
    # 启动服务
    log_info "启动服务 (单容器模式)..."
    if docker_compose_with_custom_params up -d; then
        log_success "服务启动成功"
        write_log "服务启动成功"
        echo ""
        log_info "服务地址："
        log_info "- API: http://localhost:${CUSTOM_API_PORT}"
        log_info "- UI: http://localhost:${CUSTOM_UI_PORT}"
        return 0
    else
        log_error "服务启动失败"
        write_log "服务启动失败"
        echo ""
        log_info "请尝试以下解决方案："
        log_info "1. 检查 Docker 服务是否正常运行"
        log_info "2. 检查 docker-compose.yml 文件是否存在且正确"
        log_info "3. 查看详细日志进行诊断"
        return 1
    fi
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
    i=1
    local api_port="${CUSTOM_API_PORT:-5001}"
    while [ $i -le $max_retries ]; do
        log_info "API 健康检查尝试 $i/$max_retries (端口 $api_port)..."
        
        if timeout 10 curl -s http://localhost:$api_port/health >/dev/null 2>&1; then
            log_success "API 服务 (端口 $api_port) 运行正常"
            api_healthy=true
            break
        elif timeout 5 curl -s http://localhost:$api_port >/dev/null 2>&1; then
            log_success "API 服务 (端口 $api_port) 响应正常 (health endpoint 不可用)"
            api_healthy=true
            break
        else
            # 检查端口是否被占用
            if netstat -tuln 2>/dev/null | grep -q ":$api_port " || ss -tuln 2>/dev/null | grep -q ":$api_port "; then
                log_warning "API 服务 (端口 $api_port) 端口已开启，但服务未完全就绪"
                if [ $i -eq $max_retries ]; then
                    log_warning "API 服务启动超时，但端口已占用"
                fi
            else
                log_warning "API 服务 (端口 $api_port) 可能未启动"
                if [ $i -eq $max_retries ]; then
                    all_healthy=false
                fi
            fi
        fi
        
        if [ $i -lt $max_retries ]; then
            log_info "等待 ${retry_interval}s 后重试..."
            sleep $retry_interval
        fi
        i=$((i + 1))
    done
    
    # 检查 UI 服务
    log_info "检查 UI 服务健康状态..."
    local ui_healthy=false
    i=1
    local ui_port="${CUSTOM_UI_PORT:-5002}"
    while [ $i -le $max_retries ]; do
        log_info "UI 健康检查尝试 $i/$max_retries (端口 $ui_port)..."
        
        if timeout 10 curl -s http://localhost:$ui_port >/dev/null 2>&1; then
            log_success "UI 服务 (端口 $ui_port) 运行正常"
            ui_healthy=true
            break
        else
            # 检查端口是否被占用
            if netstat -tuln 2>/dev/null | grep -q ":$ui_port " || ss -tuln 2>/dev/null | grep -q ":$ui_port "; then
                log_warning "UI 服务 (端口 $ui_port) 端口已开启，可能仍在启动中"
                if [ $i -eq $max_retries ]; then
                    log_warning "UI 服务启动超时，但端口已占用"
                    ui_healthy=true
                fi
            else
                log_warning "UI 服务 (端口 $ui_port) 可能未启动"
                if [ $i -eq $max_retries ]; then
                    all_healthy=false
                fi
            fi
        fi
        
        if [ $i -lt $max_retries ] && [ "$ui_healthy" = false ]; then
            log_info "等待 ${retry_interval}s 后重试..."
            sleep $retry_interval
        fi
        i=$((i + 1))
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
        log_info "   2. 查看服务日志: 选择菜单项 '4) 查看服务日志'"
        log_info "   3. 检查端口占用: netstat -tuln | grep :80"
    fi
    
    return 0
}

# 环境配置检查函数
check_environment_config() {
    log_info "执行环境配置检查..."
    
    # 检查 Python 是否可用
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        log_warning "Python 未安装，跳过环境配置检查"
        return 1
    fi
    
    # 选择 Python 命令
    local python_cmd=""
    if command -v python3 &> /dev/null; then
        python_cmd="python3"
    elif command -v python &> /dev/null; then
        python_cmd="python"
    fi
    
    # 检查环境检查脚本是否存在
    local env_checker_script="scripts/env_checker.py"
    if [ ! -f "$env_checker_script" ]; then
        log_warning "环境检查脚本不存在: $env_checker_script"
        return 1
    fi
    
    # 运行环境配置检查
    log_info "运行环境配置检查脚本..."
    if $python_cmd "$env_checker_script"; then
        log_success "环境配置检查完成"
        return 0
    else
        local exit_code=$?
        log_warning "环境配置检查返回非零退出码: $exit_code"
        return 1
    fi
}

# 预检查必要配置文件
preflight_check() {
    log_info "执行启动前检查..."
    local check_passed=true
    
    # 1. 环境配置检查
    log_info "检查环境配置..."
    if ! check_environment_config; then
        log_warning "环境配置检查存在问题，但将继续启动"
    fi
    
    # 2. 检查必要的配置文件
    local required_files="docker-compose.yml"
    for file in $required_files; do
        if [ ! -f "$file" ]; then
            log_warning "缺少配置文件: $file"
            check_passed=false
        else
            log_info "配置文件存在: $file"
        fi
    done
    
    # 3. 检查 Docker 是否可用
    if ! docker info &> /dev/null; then
        log_error "Docker 不可用，请确保 Docker 服务正在运行"
        check_passed=false
    fi
    
    # 4. 检查端口是否被占用
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
    local ports_in_use=""
    
    # 检查主要端口
    local check_ports="5001 5002 6379"
    for port in $check_ports; do
        if netstat -tuln 2>/dev/null | grep -q ":${port} " || ss -tuln 2>/dev/null | grep -q ":${port} "; then
            ports_in_use="$ports_in_use $port"
            log_warning "端口 $port 已被占用"
        fi
    done
    
    if [ -z "$ports_in_use" ]; then
        log_info "所有必要端口都可用"
        return 0
    else
        log_warning "发现端口被占用: $ports_in_use"
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

# 拉取最新 Docker 镜像
pull_latest_images() {
    log_info "拉取最新 Docker 镜像..."
    write_log "拉取最新镜像"
    
    echo ""
    echo "📦 镜像拉取选项："
    echo "1) 基础模式镜像"
    echo "2) Redis 模式镜像 (包含 Redis)"
    echo "3) 所有镜像"
    echo "0) 取消"
    echo ""
    read -p "请选择 [1-3, 0]: " choice
    
    case $choice in
        1)
            log_info "拉取基础模式镜像..."
            if docker_compose pull; then
                log_success "基础模式镜像拉取完成"
                write_log "基础模式镜像拉取成功"
            else
                log_error "基础模式镜像拉取失败"
                write_log "基础模式镜像拉取失败"
                return 1
            fi
            ;;
        2)
            log_info "拉取 Redis 模式镜像..."
            # 临时设置使用 single compose 文件
            local old_compose_file="$CUSTOM_COMPOSE_FILE"
            export CUSTOM_COMPOSE_FILE="docker-compose.single.yml"
            
            if COMPOSE_PROFILES=redis docker_compose pull; then
                log_success "Redis 模式镜像拉取完成"
                write_log "Redis 模式镜像拉取成功"
            else
                log_error "Redis 模式镜像拉取失败"
                write_log "Redis 模式镜像拉取失败"
                export CUSTOM_COMPOSE_FILE="$old_compose_file"
                return 1
            fi
            
            # 恢复原来的 compose 文件设置
            export CUSTOM_COMPOSE_FILE="$old_compose_file"
            ;;
        3)
            log_info "拉取所有镜像..."
            local pull_success=true
            
            # 拉取基础镜像
            if docker_compose pull; then
                log_success "基础镜像拉取完成"
            else
                log_error "基础镜像拉取失败"
                pull_success=false
            fi
            
            # 拉取 Redis 镜像 (使用 single compose 文件)
            local old_compose_file="$CUSTOM_COMPOSE_FILE"
            export CUSTOM_COMPOSE_FILE="docker-compose.single.yml"
            
            if COMPOSE_PROFILES=redis docker_compose pull; then
                log_success "Redis 镜像拉取完成"
            else
                log_error "Redis 镜像拉取失败"
                pull_success=false
            fi
            
            # 恢复原来的 compose 文件设置
            export CUSTOM_COMPOSE_FILE="$old_compose_file"
            
            if [ "$pull_success" = true ]; then
                log_success "所有镜像拉取完成"
                write_log "所有镜像拉取成功"
            else
                log_warning "部分镜像拉取失败"
                write_log "部分镜像拉取失败"
                return 1
            fi
            ;;
        0)
            log_info "取消镜像拉取"
            return 0
            ;;
        "")
            log_warning "请输入有效的选项"
            pull_latest_images
            ;;
        *)
            log_warning "无效选择：'$choice'，请输入 1、2、3 或 0"
            pull_latest_images
            ;;
    esac
    
    return 0
}

# 主函数
main() {
    # 初始化启动日志
    init_startup_log
    
    echo ""
    echo "🎯 AI-CodeReview 智能启动助手"
    echo "版本: 3.0 | 单容器架构 - API+Worker+UI 三合一"
    echo ""

    # 执行启动前检查
    preflight_check

    # 检查环境和下载配置文件
    if ! download_compose_files; then
        log_warning "配置文件下载失败，但将尝试继续运行"
    fi
    
    if ! check_docker; then
        log_warning "Docker 环境检查失败，某些功能可能不可用"
        log_info "您仍可以使用菜单选项 7 来安装 Docker 环境"
    fi
    
    if ! create_directories; then
        log_warning "目录创建存在问题，但将尝试继续运行"
    fi

    while true; do
        show_deployment_menu
        read -p "请选择操作 [0-9]: " choice
        
        # 处理空输入
        if [ -z "$choice" ]; then
            log_warning "请输入有效的选项"
            continue
        fi

        case $choice in
            1)
                start_service_menu
                local exit_code=$?
                if [ $exit_code -eq 0 ]; then
                    check_service_health
                fi
                ;;
            2)
                stop_service
                ;;
            3)
                show_service_status
                ;;
            4)
                show_service_logs
                ;;
            5)
                restart_service
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
                pull_latest_images
                ;;
            9)
                log_info "开始下载配置文件..."
                download_compose_files
                ;;
            0)
                log_info "感谢使用 AI-CodeReview!"
                write_log "用户退出程序"
                exit 0
                ;;
            "")
                log_warning "请输入有效的选项"
                ;;
            *)
                log_warning "无效选择：'$choice'，请输入 0-9 之间的数字"
                echo "提示: 输入 0 退出程序"
                ;;
        esac

        echo ""
        read -p "按回车键继续..." dummy
    done
}

# 脚本入口
main "$@"
