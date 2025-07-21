import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import { notifyUserLogin } from "@/app/actions/auth";

const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      // Persist the OAuth access_token and or the user id to the token right after signin
      if (account) {
        token.accessToken = account.access_token;
      }

      // Try different ways to get the user ID from Google profile
      if (profile && typeof profile === "object") {
        // Google OAuth might provide ID in different fields
        if ("id" in profile) {
          token.id = profile.id as string;
        } else if ("sub" in profile) {
          token.id = profile.sub as string;
        } else if ("user_id" in profile) {
          token.id = profile.user_id as string;
        }
      }

      return token;
    },
    async session({ session, token }) {
      // Send properties to the client, like an access_token and user id from a provider.
      session.accessToken = token.accessToken as string;

      // Use token.id or fallback to email as user ID
      session.user!.id =
        (token.id as string) || session.user?.email || "unknown";

      return session;
    },
    async signIn({ user, account, profile }) {
      // Call the server action to notify backend about user login
      if (user && account) {
        const userId =
          profile && typeof profile === "object" && "id" in profile
            ? (profile.id as string)
            : profile && typeof profile === "object" && "sub" in profile
              ? (profile.sub as string)
              : user.email || user.id;

        const session = {
          user: {
            id: userId,
            email: user.email,
            name: user.name,
            image: user.image,
          },
          accessToken: account.access_token,
        };

        // Call the server action asynchronously (don't await to avoid blocking sign-in)
        notifyUserLogin(session);
      }

      return true;
    },
  },
});

export { handler as GET, handler as POST };
