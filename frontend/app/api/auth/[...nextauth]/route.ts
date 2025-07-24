import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";

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
  },
});

export { handler as GET, handler as POST };
