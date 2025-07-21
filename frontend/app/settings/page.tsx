"use client";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  Bookmark,
  ChefHat,
  Eye,
  Heart,
  LogOut,
  Monitor,
  Moon,
  Sun,
  Trash2,
  User,
} from "lucide-react";
import { signOut, useSession } from "next-auth/react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { toast } from "sonner";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { data: session } = useSession();

  // User stats state
  const [userStats, setUserStats] = useState<{
    num_liked: number;
    num_saved: number;
    num_viewed: number;
    favorite_cuisine: string;
  } | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  useEffect(() => {
    const fetchStats = async () => {
      if (!session?.user?.id) return;
      setStatsLoading(true);
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;
        const res = await fetch(`${apiUrl}/users/${session.user.id}/stats`);
        if (!res.ok) throw new Error("Failed to fetch user stats");
        const data = await res.json();
        setUserStats({
          num_liked: data.num_liked,
          num_saved: data.num_saved,
          num_viewed: data.num_viewed,
          favorite_cuisine: data.favorite_cuisine || "-",
        });
      } catch (err) {
        toast.error("Failed to load user stats");
      } finally {
        setStatsLoading(false);
      }
    };
    fetchStats();
  }, [session?.user?.id]);

  const deleteAccount = async () => {
    if (!session?.user?.id) return;
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const res = await fetch(`${apiUrl}/users/${session.user.id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete account");
      toast.success("Account deleted successfully");
      signOut();
    } catch (error) {
      toast.error("Failed to delete account");
    }
  };

  const getThemeIcon = (themeValue: string) => {
    switch (themeValue) {
      case "light":
        return <Sun className="h-4 w-4" />;
      case "dark":
        return <Moon className="h-4 w-4" />;
      default:
        return <Monitor className="h-4 w-4" />;
    }
  };

  const getThemeLabel = (themeValue: string) => {
    switch (themeValue) {
      case "light":
        return "Light";
      case "dark":
        return "Dark";
      default:
        return "System";
    }
  };

  return (
    <div className="space-y-4 px-4 pt-4 pb-4">
      {/* Profile Information */}
      <Card>
        <CardContent className="space-y-4">
          {/* Profile Picture and Display Name/Email */}
          <div className="flex items-center gap-4">
            <Avatar className="h-16 w-16">
              <AvatarImage src={session?.user?.image || undefined} />
              <AvatarFallback className="bg-orange-100 text-orange-500 dark:bg-orange-900">
                <User className="h-8 w-8" />
              </AvatarFallback>
            </Avatar>
            <div className="flex flex-col justify-center">
              <span className="text-foreground text-2xl font-semibold">
                {session?.user?.name || ""}
              </span>
              <span className="text-muted-foreground text-sm">
                {session?.user?.email || ""}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Your Recipe Journey</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {statsLoading || !userStats ? (
            <div className="flex justify-center py-8">
              <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-orange-500"></div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className="mb-2 flex items-center justify-center">
                  <Heart className="mr-1 h-5 w-5 text-green-500" />
                  <span className="text-foreground text-2xl font-bold">
                    {userStats.num_liked}
                  </span>
                </div>
                <p className="text-muted-foreground text-sm">Recipes Liked</p>
              </div>
              <div className="text-center">
                <div className="mb-2 flex items-center justify-center">
                  <Bookmark className="mr-1 h-5 w-5 text-orange-500" />
                  <span className="text-foreground text-2xl font-bold">
                    {userStats.num_saved}
                  </span>
                </div>
                <p className="text-muted-foreground text-sm">Recipes Saved</p>
              </div>
              <div className="text-center">
                <div className="mb-2 flex items-center justify-center">
                  <Eye className="mr-1 h-5 w-5 text-blue-500" />
                  <span className="text-foreground text-2xl font-bold">
                    {userStats.num_viewed}
                  </span>
                </div>
                <p className="text-muted-foreground text-sm">Recipes Viewed</p>
              </div>
              <div className="text-center">
                <div className="mb-2 flex items-center justify-center">
                  <ChefHat className="mr-1 h-5 w-5 text-purple-500" />
                  <span className="text-foreground text-lg font-bold">
                    {userStats.favorite_cuisine}
                  </span>
                </div>
                <p className="text-muted-foreground text-sm">
                  Favorite Cuisine
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Theme Settings */}
      <Card className="gap-2">
        <CardHeader>
          <CardTitle className="text-lg">Appearance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Theme</span>
            <Select value={theme} onValueChange={setTheme}>
              <SelectTrigger className="w-32">
                <SelectValue>
                  <div className="flex items-center gap-2">
                    {getThemeIcon(theme || "system")}
                    <span>{getThemeLabel(theme || "system")}</span>
                  </div>
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">
                  <div className="flex items-center gap-2">
                    <Sun className="h-4 w-4" />
                    <span>Light</span>
                  </div>
                </SelectItem>
                <SelectItem value="dark">
                  <div className="flex items-center gap-2">
                    <Moon className="h-4 w-4" />
                    <span>Dark</span>
                  </div>
                </SelectItem>
                <SelectItem value="system">
                  <div className="flex items-center gap-2">
                    <Monitor className="h-4 w-4" />
                    <span>System</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Authentication */}
      <Card className="gap-2">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            Authentication
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            variant="outline"
            className="w-full"
            onClick={() => signOut()}
          >
            <LogOut className="mr-2 h-4 w-4" />
            Log Out
          </Button>
          <Separator />
          {/* Delete Account */}
          <div className="space-y-2">
            <Label className="text-red-600">Danger Zone</Label>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" size="sm" className="w-full">
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete Account
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                  <AlertDialogDescription className="space-y-2 text-left">
                    <p>
                      This action cannot be undone. This will permanently delete
                      your account and remove all your data from our servers.
                    </p>
                    <p className="font-medium">This includes:</p>
                    <ul className="list-inside list-disc space-y-1 text-sm">
                      <li>
                        All saved recipes ({userStats?.num_saved || 0} recipes)
                      </li>
                      <li>Your recipe preferences and history</li>
                      <li>Your profile information</li>
                      <li>All account data and statistics</li>
                    </ul>
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={deleteAccount}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete Account
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
            <p className="text-muted-foreground text-xs">
              This will permanently delete all your data and cannot be undone.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
