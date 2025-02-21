/**
 * Handler that will be called during the execution of a PostLogin flow.
 *
 * @param {Event} event - Details about the user and the context in which they are logging in.
 * @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
 */

const auth0 = require("auth0-js"); // why node.js sdk doesn't have buildAuthorizeUrl?
const { ManagementClient, AuthenticationClient } = require("auth0");
const jwt = require("jsonwebtoken");
const jwksClient = require("jwks-rsa");
const axios = require("axios");
const crypto = require("crypto");

const interactive_login = new RegExp("^oidc-");
const linking_resource_server = "my-account";

const canPromptMfa = (user) =>
  user.enrolledFactors && user.enrolledFactors.length > 0;
const hasDoneMfa = (event) =>
  event.authentication.methods.some((m) => m.name === "mfa");
const mapEnrolledToFactors = (user) =>
  user.enrolledFactors.map((f) =>
    f.method === "sms"
      ? { type: "phone", options: { preferredMethod: "sms" } }
      : { type: f.method }
  );
const hasLinkedIdentityWithConnection = (user, connection) =>
  user.identities.some((i) => i.connection === connection);
const makeNonce = (event) =>
  crypto
    .createHash("sha256")
    .update(event.user.user_id + event.request.ip)
    .digest("hex")
    .substring(0, 32);

exports.onExecutePostLogin = async (event, api) => {
  const protocol = event?.transaction?.protocol || "unknown";

  if (!interactive_login.test(protocol)) {
    console.log(`skip since protocol is not interactive: ${protocol}`);
    return;
  }

  console.log(`protocol: ${protocol}, client_id: ${event.client.client_id}`);

  const { clientId } = event.secrets || {};

  if (event.client.client_id === clientId) {
    //console.log(`running inner transaction for event: ${JSON.stringify(event)}`);

    if (canPromptMfa(event.user) && !hasDoneMfa(event)) {
      console.log("mfa required in inner tx.");
      api.authentication.challengeWithAny(mapEnrolledToFactors(event.user));
    } else {
      console.log("mfa not required in inner tx.");
    }

    return;
  }

  const { identifier: resource_server } = event?.resource_server;
  console.log(`resource_server: ${resource_server}`);

  if (resource_server !== linking_resource_server) {
    console.log(
      `skip since resource-server is not target ${linking_resource_server}: ${resource_server}`
    );
    return;
  }

  const { requested_scopes } = event?.transaction;

  let requestedOperation = null;

  if (Array.isArray(requested_scopes) && requested_scopes.length > 0) {
    if (requested_scopes.includes("link_account")) {
      requestedOperation = "link_account";
    } else if (requested_scopes.includes("unlink_account")) {
      requestedOperation = "unlink_account";
    }
  }
  // const requestLinkAccountScope = Array.isArray(requested_scopes)
  //     && requested_scopes.length > 0
  //     && (requested_scopes.includes('link_account') || requested_scopes.includes('unlink_account'));

  // if (!requestLinkAccountScope ) {
  //     console.log(`skip since no link_account scope present`);
  //     return;
  // }

  if (requestedOperation === null) {
    console.log(
      "Error: Missing required scopes. Expecting either link_account or unlink_account."
    );
    return;
  }

  const { id_token_hint } = event?.request?.query;
  console.log(`id_token_hint: ${id_token_hint}`);

  if (!id_token_hint) {
    console.log(`skip since no id_token_hint present`);
    return;
  }

  const {
    requested_connection: requested_connection,
    requested_connection_scopes: requested_connection_scopes,
  } = event.request.query;

  if (!requested_connection) {
    console.log(`skip since no requested_connection defined`);
    return;
  }

  // already has a link with upstream connection ?
  const linkedStatus = hasLinkedIdentityWithConnection(
    event.user,
    requested_connection
  );
  if (requestedOperation == "link_account" && linkedStatus) {
    console.log(
      `user already has a linked profile against request connection: ${requested_connection}`
    );
    return;
  }

  if (requestedOperation == "unlink_account" && !linkedStatus) {
    console.log(
      `user does not have a linked profile against requested connection: ${requested_connection}`
    );
    return;
  }

  const { domain } = event.secrets || {};

  const incoming_token = await verifyIdToken(api, id_token_hint, domain); // todo: optional auth_time claim check

  if (incoming_token.sub !== event?.user?.user_id) {
    api.access.deny("sub mismatch");
    api.session.revoke("sub mismatch");
    console.log(
      `logging out due to sub mismatch. expected ${event?.user?.user_id} received: ${incoming_token.sub}`
    );
    return;
  }

  //console.log(`running outer transaction for event: ${JSON.stringify(event, null, 2)}`);

  /*
    // nonce when doing PAR
    const nonce = event.transaction.linking_id;
    console.log(`nonce for inner tx: ${nonce}`);
    */

  switch (requestedOperation) {
    case "link_account":
      const nonce = makeNonce(event);
      console.log(`nonce for inner tx: ${nonce}`);

      const authClient = new auth0.Authentication({
        domain,
        clientID: event.secrets.clientId,
      });

      // todo: PKCE
      const nestedAuthorizeURL = authClient.buildAuthorizeUrl({
        redirectUri: `https://${domain}/continue`,
        nonce,
        responseType: "code",
        prompt: "login",
        connection: requested_connection,
        login_hint: event.user.email,
        scope: requested_connection_scopes ?? "openid profile email",
      });

      console.log(`redirecting to ${nestedAuthorizeURL}`);
      api.redirect.sendUserTo(nestedAuthorizeURL);
      break;
    case "unlink_account":
      await unLink(event, api, requested_connection);
      break;
    default:
      console.log("Error: Invalid operation.");
  }
};

exports.onContinuePostLogin = async (event, api) => {
  //console.log(`onContinuePostLogin event: ${JSON.stringify(event)}`);

  const { domain } = event.secrets || {};

  const { code } = event.request.query;
  const client_id = event.secrets.clientId;

  const id_token_str = await exchange(
    domain,
    client_id,
    event.secrets.clientSecret,
    code,
    `https://${domain}/continue`
  );
  console.log(`id_token string from exchange: ${id_token_str}`);

  if (!id_token_str) {
    api.access.deny("error in exchange");
    return;
  }

  const id_token = await verifyIdToken(
    api,
    id_token_str,
    domain,
    client_id,
    makeNonce(event)
  );

  // optional check: upstream to supply verified emails only
  if (id_token.email_verified !== true) {
    console.log(
      `skipped linking, email not verified in nested tx user: ${id_token.email}`
    );
    return;
  }

  /* optional check: If you are only linking users with the same email, you can uncomment this
    if (event.user.email !== id_token.email) {
        api.access.deny('emails do not match');
        return;
    }
    */

  await linkAndMakePrimary(event, api, id_token.sub);
};

async function linkAndMakePrimary(event, api, upstream_sub) {
  //console.log(`linking ${event.user.user_id} under ${primary_sub}`);

  const { domain } = event.secrets;

  let { value: token } = api.cache.get("management-token") || {};

  if (!token) {
    const { clientId, clientSecret } = event.secrets || {};

    const cc = new AuthenticationClient({ domain, clientId, clientSecret });

    try {
      const { data } = await cc.oauth.clientCredentialsGrant({
        audience: `https://${domain}/api/v2/`,
      });

      token = data?.access_token;

      if (!token) {
        console.log("failed get api v2 cc token");
        return;
      }
      console.log("cache MIS m2m token!");

      const result = api.cache.set("management-token", token, {
        ttl: data.expires_in * 1000,
      });

      if (result?.type === "error") {
        console.log(
          "failed to set the token in the cache with error code",
          result.code
        );
      }
    } catch (err) {
      console.log("failed calling cc grant", err);
      return;
    }
  }

  const client = new ManagementClient({ domain, token });

  const { user_id, provider } = event.user.identities[0];

  // Have either A or B

  // (A) this block links current user to upstream user, making this user secondary
  /*
    try {
        await client.users.link({id: upstream_sub}, {user_id, provider});
        console.log(`link successful ${upstream_sub} to ${user_id} of provider: ${provider}`);
        api.authentication.setPrimaryUser(upstream_sub);
        console.log(`changed primary from ${event.user.user_id} to ${primary_sub}`);
    } catch (err) {
        console.log(`unable to link, no changes. error: ${JSON.stringify(err)}`);
        return;
    }
    */

  // (B) this block links current user to upstream user, keeping this user primary
  const firstPipeIndex = upstream_sub.indexOf("|");
  const [up_provider, up_user_id] = [
    upstream_sub.slice(0, firstPipeIndex),
    upstream_sub.slice(firstPipeIndex + 1),
  ];
  try {
    await client.users.link(
      { id: `${provider}|${user_id}` },
      { user_id: up_user_id, provider: up_provider }
    );
    console.log(
      `link successful current user to ${up_user_id} of provider: ${up_provider}`
    );
  } catch (err) {
    console.log(`unable to link, no changes. error: ${JSON.stringify(err)}`);
  }
}

async function verifyIdToken(api, id_token, domain, client_id, nonce) {
  function getKey(header, callback) {
    const { value: signingKey } = api.cache.get(`key-${header.kid}`) || {};
    if (!signingKey) {
      console.log(`cache MIS signing key: ${header.kid}`);
      const client = jwksClient({
        jwksUri: `https://${domain}/.well-known/jwks.json`,
      });

      client.getSigningKey(header.kid, (err, key) => {
        if (err) {
          console.log("failed to download signing key: ", err.message);
          return callback(err);
        }
        const signingKey = key.publicKey || key.rsaPublicKey;

        const result = api.cache.set(`key-${header.kid}`, signingKey);

        if (result?.type === "error") {
          console.log("failed to set signing key in the cache", result.code);
        }
        callback(null, signingKey);
      });
    } else {
      callback(null, signingKey);
    }
  }

  const signature = {
    issuer: `https://${domain}/`,
    algorithms: "RS256",
  };

  if (nonce) {
    signature.nonce = nonce;
  }

  if (client_id) {
    signature.client_id = client_id;
  }

  console.log(
    `jwt.verify id_token: ${id_token} against signature: ${JSON.stringify(
      signature
    )}`
  );

  return new Promise((resolve, reject) => {
    jwt.verify(id_token, getKey, signature, (err, decoded) => {
      if (err) reject(err);
      else resolve(decoded);
    });
  });
}

async function exchange(domain, client_id, client_secret, code, redirect_uri) {
  console.log(`exchanging code: ${code}`);

  const {
    data: { id_token },
  } = await axios({
    method: "post",
    url: `https://${domain}/oauth/token`,
    data: {
      client_id,
      client_secret,
      code,
      grant_type: "authorization_code",
      redirect_uri,
    },
    headers: {
      "Content-Type": "application/json",
    },
    timeout: 5000, // 5 sec
  });

  return id_token;
}

async function unLink(event, api, connection_to_unlink) {
  const { domain } = event.secrets;

  let { value: token } = api.cache.get("management-token") || {};

  if (!token) {
    const { clientId, clientSecret } = event.secrets || {};

    const cc = new AuthenticationClient({ domain, clientId, clientSecret });

    try {
      const { data } = await cc.oauth.clientCredentialsGrant({
        audience: `https://${domain}/api/v2/`,
      });

      token = data?.access_token;

      if (!token) {
        console.log("failed get api v2 cc token");
        return;
      }
      console.log("cache MIS m2m token!");

      console.log(token);

      const result = api.cache.set("management-token", token, {
        ttl: data.expires_in * 1000,
      });

      if (result?.type === "error") {
        console.log(
          "failed to set the token in the cache with error code",
          result.code
        );
      }
    } catch (err) {
      console.log("failed calling cc grant", err);
      return;
    }
  }

  const client = new ManagementClient({ domain, token });

  // Function to unlink a user identity
  async function unlinkIdentity(primary_id, connection, unlink_id) {
    console.log(primary_id, connection, unlink_id);
    try {
      const response = await client.users.unlink({
        id: primary_id, // Primary user ID (who has linked accounts)
        provider: connection, // e.g., "google-oauth2"
        user_id: unlink_id, // ID of the linked account
      });
      console.log("Successfully unlinked identity:", response);
    } catch (error) {
      console.error("Error unlinking identity:", error.response?.data || error);
    }
  }

  // Run the unlink function
  const unlinkPromises = event.user.identities
    .filter((x) => x.connection === connection_to_unlink)
    .map((x) =>
      unlinkIdentity(
        event.user.identities[0].provider +
          "|" +
          event.user.identities[0].userId,
        connection_to_unlink,
        x.userId
      )
    );

  await Promise.all(unlinkPromises);
}
