// Import the necessary Firebase Admin SDK modules.
// The Admin SDK provides privileged access to Firebase services.
const { initializeApp } = require("firebase-admin/app");
const { getAuth } = require("firebase-admin/auth");
const { getFirestore } = require("firebase-admin/firestore");
const { onCall, HttpsError } = require("firebase-functions/v2/https");

// Initialize the Firebase Admin App.
// This is done once when the function is deployed.
initializeApp();

/**
 * A callable Cloud Function to handle new user signups with an invite code.
 * This function provides a secure way to control who can create an account.
 */
exports.createNewUser = onCall(async (request) => {
  // Extract email, password, and the invite code from the client's request.
  const { email, password, inviteCode } = request.data;

  // --- Input Validation ---
  if (!email || !password || !inviteCode) {
    // If any of the required fields are missing, throw an error.
    // This prevents incomplete requests from proceeding.
    throw new HttpsError(
      "invalid-argument",
      "Missing email, password, or invite code."
    );
  }

  // Get a reference to the Firestore database.
  const db = getFirestore();
  
  // Create a reference to the specific invite code document in the /invites collection.
  const inviteRef = db.collection("invites").doc(inviteCode);
  
  // --- Secure Backend Logic ---
  try {
    // Atomically read and update the invite code document in a transaction.
    // A transaction ensures that no one else can use the same invite code simultaneously.
    const newUserData = await db.runTransaction(async (transaction) => {
      const inviteDoc = await transaction.get(inviteRef);

      // Check if the invite code document exists.
      if (!inviteDoc.exists) {
        throw new HttpsError("not-found", "Invalid invite code.");
      }
      
      // Check if the invite code has already been used.
      if (inviteDoc.data().used) {
        throw new HttpsError(
          "permission-denied",
          "This invite code has already been used."
        );
      }

      // --- Create the User ---
      // If the code is valid, use the Admin SDK to create the new Firebase Auth user.
      // This is a privileged operation that can only be done from a secure backend.
      const userRecord = await getAuth().createUser({
        email: email,
        password: password,
      });

      // Mark the invite code as used by this new user's UID.
      // This prevents the code from being used again.
      transaction.update(inviteRef, {
        used: true,
        usedBy: userRecord.uid,
        usedAt: new Date(),
      });
      
      // Return the new user's UID and email to be sent back to the client.
      return { uid: userRecord.uid, email: userRecord.email };
    });

    // If the transaction is successful, return the new user's data.
    console.log(`Successfully created new user: ${newUserData.email}`);
    return {
      status: "success",
      message: "User created successfully!",
      user: newUserData,
    };

  } catch (error) {
    // If any part of the process fails, log the error and re-throw it.
    // The HttpsError from above will be passed back to the client.
    console.error("Error creating new user:", error);
    throw error;
  }
});
