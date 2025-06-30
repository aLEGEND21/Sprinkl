"use client";

import { signIn, signOut, useSession } from "next-auth/react";

export default function Home() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4 text-white">Loading...</h1>
        </div>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4 text-white">
            Welcome to FoodApp
          </h1>
          <p className="text-gray-300 mb-6">Please log in to continue</p>
          <button
            onClick={() => signIn("google")}
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
          >
            Log In with Google
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-8 bg-gray-900">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-white">Welcome to FoodApp</h1>
          <button
            onClick={() => signOut()}
            className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded"
          >
            Log Out
          </button>
        </div>

        <div className="bg-gray-800 shadow-lg rounded-lg p-6 border border-gray-700">
          <h2 className="text-xl font-semibold mb-4 text-white">
            Session Information
          </h2>
          <div className="bg-gray-900 p-4 rounded border border-gray-600 overflow-auto max-h-96">
            <pre className="text-sm whitespace-pre-wrap text-gray-200 font-mono">
              {JSON.stringify(session, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
