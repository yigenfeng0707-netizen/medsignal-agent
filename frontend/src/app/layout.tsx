import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { cn } from "@/lib/utils";
import { Sidebar } from "@/components/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ConditionalSidebar } from "@/components/conditional-sidebar";
import { UserProvider } from "@/lib/user-context";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "医保智脑 - YiBaoZhiNao",
  description: "基于可信数据空间的个人医保智能体",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className={cn(geistSans.variable, geistMono.variable)}>
      <body className="antialiased">
        <UserProvider>
          <TooltipProvider>
            <ConditionalSidebar>{children}</ConditionalSidebar>
          </TooltipProvider>
        </UserProvider>
      </body>
    </html>
  );
}
