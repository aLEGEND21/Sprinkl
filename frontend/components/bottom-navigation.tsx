"use client";

import { useRouter, usePathname } from "next/navigation";
import { Home, Search, Bookmark, Settings } from "lucide-react";

export function BottomNavigation() {
  const router = useRouter();
  const pathname = usePathname();

  const navItems = [
    {
      id: "for-you",
      label: "For You",
      icon: Home,
      path: "/protected/fyp",
    },
    {
      id: "search",
      label: "Search",
      icon: Search,
      path: "/protected/search",
    },
    {
      id: "saved",
      label: "Saved",
      icon: Bookmark,
      path: "/protected/saved",
    },
    {
      id: "settings",
      label: "Settings",
      icon: Settings,
      path: "/protected/settings",
    },
  ];

  const handleNavigation = (path: string) => {
    router.push(path);
  };

  return (
    <>
      {/* This is a hack to ensure the bottom navigation is positioned correctly on the mobile PWA */}
      <div className="bg-background border-border safe-area-pb fixed right-0 bottom-0 left-0 z-50 w-full border-t px-2 py-2 md:relative md:right-auto md:bottom-auto md:left-auto md:z-auto">
        <div className="flex items-center justify-around">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.path;

            return (
              <button
                key={item.id}
                onClick={() => handleNavigation(item.path)}
                className={`flex flex-col items-center justify-center rounded-lg px-3 py-2 transition-colors duration-200 ${
                  isActive
                    ? "bg-orange-50 text-orange-500 dark:bg-orange-950"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
              >
                <Icon
                  className={`mb-1 h-5 w-5 ${isActive ? "text-orange-500" : "text-muted-foreground"}`}
                />
                <span
                  className={`text-xs font-medium ${isActive ? "text-orange-500" : "text-muted-foreground"}`}
                >
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </>
  );
}
