# 阶段 1: 构建阶段
FROM node:20-alpine AS builder
WORKDIR /app

RUN apk add --no-cache openssl

# 拷贝 package.json 和 lock 文件
COPY package*.json ./
# 安装依赖
RUN npm install --legacy-peer-deps

# 拷贝源码
COPY . .

# 生成 Prisma Client (如果有数据库操作)
RUN npx prisma generate

# 执行构建
RUN npm run build

# 阶段 2: 运行阶段
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV production

RUN apk add --no-cache openssl

# 只需要从构建阶段拷贝必要的文件
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# 暴露 Next.js 默认端口
EXPOSE 3000

# 启动应用
CMD ["npm", "start"]
