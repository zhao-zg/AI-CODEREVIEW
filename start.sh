#!/bin/bash

# AI-CodeReview-Gitlab 智能启动脚本
# 支持多容器和单容器模式选择

set -e

# 信号处理 - 防止意外退出
trap 'echo ""; log_warning "检测到中断信号，返回主菜单..."; echo ""' INT

# Docker Compose 兼容函数
# 优先使用 docker compose，如果不可用则使用 docker-compose
docker_compose() {
    if docker compose version &> /dev/null; then
        docker compose "$@"
    elif command -v docker-compose &> /dev/null; then
        docker-compose "$@"
    else
        log_error "Docker Compose 未安装！请先安装 Docker Compose"
        return 1
    fi
}

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 和 Docker Compose
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_warning "Docker 未安装，准备安装..."
        install_docker
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_warning "Docker Compose 未安装，准备安装..."
        install_docker_compose
    fi

    log_success "Docker 环境检查通过"
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
    
    BASE_URL="https://raw.githubusercontent.com/zhao-zg/AI-CODEREVIEW-GITLAB/main"
    
    # 下载多容器配置
    if [ ! -f "docker-compose.yml" ]; then
        log_info "下载多容器配置文件..."
        curl -fsSL "${BASE_URL}/docker-compose.yml" -o docker-compose.yml
        if [ $? -eq 0 ]; then
            log_success "多容器配置文件下载完成"
        else
            log_error "多容器配置文件下载失败"
            return 1
        fi
    else
        log_info "多容器配置文件已存在"
    fi
    
    # 下载单容器配置
    if [ ! -f "docker-compose.single.yml" ]; then
        log_info "下载单容器配置文件..."
        curl -fsSL "${BASE_URL}/docker-compose.single.yml" -o docker-compose.single.yml
        if [ $? -eq 0 ]; then
            log_success "单容器配置文件下载完成"
        else
            log_error "单容器配置文件下载失败"
            return 1
        fi
    else
        log_info "单容器配置文件已存在"
    fi
    
    # 下载 Dockerfile
    if [ ! -f "Dockerfile" ]; then
        log_info "下载 Dockerfile..."
        curl -fsSL "${BASE_URL}/Dockerfile" -o Dockerfile
        if [ $? -eq 0 ]; then
            log_success "Dockerfile 下载完成"
        else
            log_warning "Dockerfile 下载失败，将使用预构建镜像"
        fi
    fi
    
    return 0
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    mkdir -p conf data log data/svn
    log_success "目录创建完成"
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
    echo "6) 安装/更新环境"
    echo "   - 安装 Docker 和 Docker Compose"
    echo "   - 下载最新配置文件"
    echo ""
    echo "7) 下载配置文件"
    echo "   - 下载/更新 docker-compose.yml"
    echo "   - 下载/更新相关配置"
    echo ""
    echo "0) 退出"
    echo "=================================================="
}

# 多容器模式菜单
multi_container_menu() {
    echo ""
    echo "🔧 多容器模式选项："
    echo "1) 基础模式 (仅 API + UI)"
    echo "2) 完整模式 (API + UI + Worker + Redis)"
    echo "0) 返回主菜单"
    echo ""
    read -p "请选择 [1-2, 0]: " choice
    
    # 处理空输入
    if [ -z "$choice" ]; then
        log_warning "请输入有效的选项"
        multi_container_menu
        return
    fi

    case $choice in
        1)
            log_info "启动多容器基础模式..."
            docker_compose up -d
            ;;
        2)
            log_info "启动多容器完整模式..."
            COMPOSE_PROFILES=worker docker_compose up -d
            ;;
        0)
            return
            ;;
        *)
            log_warning "无效选择，请重新选择"
            multi_container_menu
            ;;
    esac
}

# 单容器模式菜单
single_container_menu() {
    echo ""
    echo "🔧 单容器模式选项："
    echo "1) 基础模式 (进程队列)"
    echo "2) Redis 模式 (包含 Redis 队列)"
    echo "0) 返回主菜单"
    echo ""
    read -p "请选择 [1-2, 0]: " choice
    
    # 处理空输入
    if [ -z "$choice" ]; then
        log_warning "请输入有效的选项"
        single_container_menu
        return
    fi

    case $choice in
        1)
            log_info "启动单容器基础模式..."
            docker_compose -f docker-compose.single.yml up -d
            ;;
        2)
            log_info "启动单容器 Redis 模式..."
            COMPOSE_PROFILES=redis docker_compose -f docker-compose.single.yml up -d
            ;;
        0)
            return
            ;;
        *)
            log_warning "无效选择，请重新选择"
            single_container_menu
            ;;
    esac
}

# 停止所有服务
stop_all_services() {
    log_info "停止所有服务..."
    
    # 尝试停止多容器服务
    if docker_compose ps -q 2>/dev/null | grep -q .; then
        log_info "停止多容器服务..."
        docker_compose down
    fi
    
    # 尝试停止单容器服务
    if docker_compose -f docker-compose.single.yml ps -q 2>/dev/null | grep -q .; then
        log_info "停止单容器服务..."
        docker_compose -f docker-compose.single.yml down
    fi
    
    log_success "所有服务已停止"
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
    echo ""
    echo "📋 选择要查看的日志："
    echo "1) 多容器服务日志"
    echo "2) 单容器服务日志"
    echo "3) 特定容器日志"
    echo "0) 返回主菜单"
    echo ""
    read -p "请选择 [1-3, 0]: " choice
    
    # 处理空输入
    if [ -z "$choice" ]; then
        log_warning "请输入有效的选项"
        show_service_logs
        return
    fi

    case $choice in
        1)
            log_info "显示多容器服务日志..."
            docker_compose logs -f --tail=100
            ;;
        2)
            log_info "显示单容器服务日志..."
            docker_compose -f docker-compose.single.yml logs -f --tail=100
            ;;  
        3)
            echo ""
            echo "可用容器："
            docker ps --filter "name=ai-codereview" --format "{{.Names}}"
            echo ""
            read -p "请输入容器名称: " container_name
            if [ -n "$container_name" ]; then
                docker logs -f --tail=100 "$container_name"
            else
                log_warning "容器名称不能为空"
            fi
            ;;
        0)
            return
            ;;
        *)
            log_warning "无效选择"
            show_service_logs
            ;;
    esac
}

# 检查服务健康状态
check_service_health() {
    log_info "检查服务健康状态..."
    
    # 检查 API 服务
    if curl -s http://localhost:5001/health >/dev/null 2>&1; then
        log_success "API 服务 (端口 5001) 运行正常"
    else
        log_warning "API 服务 (端口 5001) 可能未启动或不健康"
    fi
    
    # 检查 UI 服务
    if curl -s http://localhost:5002 >/dev/null 2>&1; then
        log_success "UI 服务 (端口 5002) 运行正常"
    else
        log_warning "UI 服务 (端口 5002) 可能未启动或不健康"
    fi
}

# 主函数
main() {
    echo ""
    echo "🎯 AI-CodeReview-Gitlab 智能启动助手"
    echo "版本: 2.0 | 支持多容器/单容器部署"
    echo ""

    # 检查环境和下载配置文件
    download_compose_files || log_warning "配置文件下载失败，将尝试继续运行"
    check_docker || log_warning "Docker 环境检查失败，部分功能可能不可用"
    create_directories

    while true; do
        show_deployment_menu
        read -p "请选择操作 [0-7]: " choice
        
        # 处理空输入
        if [ -z "$choice" ]; then
            log_warning "请输入有效的选项"
            continue
        fi

        case $choice in
            1)
                multi_container_menu
                if [ $? -eq 0 ]; then
                    check_service_health
                fi
                ;;
            2)
                single_container_menu  
                if [ $? -eq 0 ]; then
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
                log_info "开始安装/更新环境..."
                install_docker
                install_docker_compose
                download_compose_files
                log_success "环境安装/更新完成"
                ;;
            7)
                log_info "开始下载配置文件..."
                download_compose_files
                log_success "配置文件下载完成"
                ;;
            0)
                log_info "感谢使用 AI-CodeReview-Gitlab!"
                exit 0
                ;;
            *)
                log_warning "无效选择：'$choice'，请输入 0-7 之间的数字"
                echo "提示: 输入 0 退出程序"
                ;;
        esac

        echo ""
        read -p "按回车键继续..." dummy
    done
}

# 脚本入口
main "$@"
