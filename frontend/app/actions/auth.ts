"use server";

export async function notifyUserLogin(session: any) {
  if (!session?.user) {
    return { success: false, error: "No user session found" };
  }

  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL!}/api/users/login`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: session.user.id,
          email: session.user.email,
          name: session.user.name,
          image: session.user.image,
        }),
      }
    );

    if (!response.ok) {
      throw new Error(`Backend API responded with status: ${response.status}`);
    }

    const result = await response.json();

    return { success: true, data: result };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}
