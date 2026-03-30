import { PrismaClient } from "@prisma/client";

const globalForPrisma = global as unknown as { prisma: PrismaClient };

export const prisma =
  globalForPrisma.prisma ||
  new PrismaClient({
    log: ["error"], // 只打印错误日志，避免控制台太吵
  });

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;