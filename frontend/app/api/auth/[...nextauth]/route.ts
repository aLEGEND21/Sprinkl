import NextAuth from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import { notifyUserLogin } from "@/app/actions/auth"

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
        token.accessToken = account.access_token
      }
      if (profile && typeof profile === 'object' && 'id' in profile) {
        token.id = profile.id as string;
      }
      return token
    },
    async session({ session, token }) {
      // Send properties to the client, like an access_token and user id from a provider.
      session.accessToken = token.accessToken as string;
      session.user!.id = token.id as string;
      return session
    },
    async signIn({ user, account, profile }) {
      // Call the server action to notify backend about user login
      if (user && account) {
        const session = {
          user: {
            id: (profile && typeof profile === 'object' && 'id' in profile) ? profile.id as string : user.id,
            email: user.email,
            name: user.name,
            image: user.image,
          },
          accessToken: account.access_token,
        };
        
        // Call the server action asynchronously (don't await to avoid blocking sign-in)
        notifyUserLogin(session).catch(error => {
          console.error('Failed to notify backend about user login:', error);
        });
      }
      
      return true;
    },
  },
})

export { handler as GET, handler as POST }
