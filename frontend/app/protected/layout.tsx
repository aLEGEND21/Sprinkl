"use client";

import { BottomNavigation } from "@/components/bottom-navigation";
import { useSession, signIn } from "next-auth/react";
import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { status } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "unauthenticated") {
      signIn("google", { callbackUrl: pathname });
    }
  }, [status, router, pathname]);

  return (
    <div>
      {/* pb-[73px] to account for height of bottom navigation */}
      <div className="pb-[73px]">
        {status === "authenticated" ? (
          children
        ) : (
          // Loading spinner
          <div className="flex h-full w-full items-center justify-center py-40">
            <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-orange-500"></div>
          </div>
        )}
      </div>
      <BottomNavigation />
    </div>
  );
}
