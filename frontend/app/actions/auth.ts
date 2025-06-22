'use server';

export async function notifyUserLogin(session: any) {
  if (!session?.user) {
    console.error('No user session found');
    return { success: false, error: 'No user session found' };
  }

  try {
    const response = await fetch(`${process.env.BACKEND_API_URL!}/api/users/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: session.user.id,
        email: session.user.email,
        name: session.user.name,
        image: session.user.image,
      }),
    });

    if (!response.ok) {
      throw new Error(`Backend API responded with status: ${response.status}`);
    }

    const result = await response.json();
    console.log('User login notification sent successfully:', result);
    
    return { success: true, data: result };
  } catch (error) {
    console.error('Failed to notify backend about user login:', error);
    return { 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown error occurred' 
    };
  }
} 