-- CreateTable
CREATE TABLE "SharedChat" (
    "id" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "snapshot" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "originalChatId" TEXT,

    CONSTRAINT "SharedChat_pkey" PRIMARY KEY ("id")
);
