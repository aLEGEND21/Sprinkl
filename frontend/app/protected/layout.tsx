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
  const { data: session, status } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "unauthenticated") {
      signIn("google", { callbackUrl: pathname });
    } else if (status === "authenticated") {
      // Notify the backend about the user login so that their account can be created if needed
      // This may run on every page nav/load, but it's not an issue for the backend
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/users/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: session?.user?.id,
          email: session?.user?.email,
          name: session?.user?.name,
          image: session?.user?.image,
        }),
      });
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
