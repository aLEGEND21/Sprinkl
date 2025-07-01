import { BottomNavigation } from "@/components/bottom-navigation";
import { Toaster } from "@/components/ui/sonner";
import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Food App Web Demo",
  description: "This is a web demo for the Food App",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning={true}>
      <body className={`${geistSans.variable} antialiased`}>
        <Providers>
          {children}
          <BottomNavigation />
          <Toaster position="top-right" richColors />
        </Providers>
      </body>
    </html>
  );
}
