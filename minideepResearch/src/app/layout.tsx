import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
// 👇 1. 引入 Toaster 组件
import { Toaster } from "sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  // 👇 2. 修改项目标题
  title: "Mini DeepResearch",
  description: "AI-powered deep research assistant",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
        {/* 👇 3. 添加 Toaster 组件，配置位置和颜色模式 */}
        <Toaster position="top-center" richColors />
      </body>
    </html>
  );
}