import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;
import java.security.KeyStore;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.io.InputStream;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class Verifier {
    private static final Logger logger = LoggerFactory.getLogger(Verifier.class);
    private static final String BOT_ITEMS_DIR = System.getenv("LOCALAPPDATA") + "/SRSBot/Bot_Items";
    private static final String TOKEN_FILE_PATH = BOT_ITEMS_DIR + "/token.txt";
    private static final String CHANNEL_FILE_PATH = BOT_ITEMS_DIR + "/channel.txt";
    private static final String ROLES_FILE_PATH = BOT_ITEMS_DIR + "/roles.txt";
    private static final String CACERT_PATH = BOT_ITEMS_DIR + "/cacert.pem";

    private static String botToken;
    private static String welcomeChannel;
    private static String pVerRole;
    private static String verifiedRole;

    private static Map<Long, String> verificationCodes = new HashMap<>();
    private static ExecutorService executorService = Executors.newFixedThreadPool(10);

    public static void main(String[] args) {
        loadConfig();
        // Add your bot initialization and event handling code here
        // For example, you might want to start the bot or listen for commands
    }

    private static void loadConfig() {
        try {
            botToken = new String(Files.readAllBytes(Paths.get(TOKEN_FILE_PATH))).trim();
            logger.debug("Bot token read successfully: {}", botToken);
        } catch (IOException e) {
            logger.error("Failed to read bot token", e);
        }

        try {
            welcomeChannel = new String(Files.readAllBytes(Paths.get(CHANNEL_FILE_PATH))).trim();
            logger.debug("Welcome channel read successfully: {}", welcomeChannel);
        } catch (IOException e) {
            logger.error("Failed to read welcome channel", e);
        }

        try {
            String[] roles = new String(Files.readAllBytes(Paths.get(ROLES_FILE_PATH))).split("\n");
            if (roles.length > 0) {
                pVerRole = roles[0].trim();
            }
            if (roles.length > 1) {
                verifiedRole = roles[1].trim();
            }
            logger.debug("P-Ver role read successfully: {}", pVerRole);
            logger.debug("Verified role read successfully: {}", verifiedRole);
        } catch (IOException e) {
            logger.error("Failed to read roles", e);
        }
    }

    private static SSLSocketFactory createSSLSocketFactory() throws Exception {
        CertificateFactory cf = CertificateFactory.getInstance("X.509");
        try (InputStream caInput = Files.newInputStream(Paths.get(CACERT_PATH))) {
            X509Certificate caCert = (X509Certificate) cf.generateCertificate(caInput);

            KeyStore keyStore = KeyStore.getInstance(KeyStore.getDefaultType());
            keyStore.load(null, null);
            keyStore.setCertificateEntry("caCert", caCert);

            TrustManagerFactory tmf = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
            tmf.init(keyStore);

            SSLContext sslContext = SSLContext.getInstance("TLS");
            sslContext.init(null, tmf.getTrustManagers(), new java.security.SecureRandom());

            return sslContext.getSocketFactory();
        }
    }

    public static void verifyCommand(String rsiUsername, long userId) {
        if (rsiUsername == null) {
            String code = String.valueOf(new Random().nextInt(900000) + 100000);
            verificationCodes.put(userId, code);
            logger.debug("Generated verification code: {} for user: {}", code, userId);
            // Send the code to the user (this part depends on your bot framework)
        } else {
            if (verificationCodes.containsKey(userId)) {
                String code = verificationCodes.get(userId);
                String url = "https://robertsspaceindustries.com/en/citizens/" + rsiUsername;
                logger.debug("Fetching RSI profile from URL: {}", url);

                CompletableFuture.runAsync(() -> {
                    try {
                        SSLSocketFactory sslSocketFactory = createSSLSocketFactory();
                        Document doc = Jsoup.connect(url).sslSocketFactory(sslSocketFactory).get();
                        Element bioElement = doc.selectFirst("div.bio div.value");
                        if (bioElement != null) {
                            String bioText = bioElement.text().trim();
                            logger.debug("Bio text found: {}", bioText);
                            if (bioText.contains(code)) {
                                // Add roles and change nickname (this part depends on your bot framework)
                                verificationCodes.remove(userId);
                                logger.debug("Removed verification code for user: {}", userId);
                            } else {
                                // Send error message to the user (this part depends on your bot framework)
                                logger.warn("Code not found in RSI bio for user: {}", userId);
                            }
                        } else {
                            // Send error message to the user (this part depends on your bot framework)
                            logger.warn("Bio section not found on RSI profile for user: {}", userId);
                        }
                    } catch (IOException e) {
                        logger.error("Error fetching RSI profile", e);
                    } catch (Exception e) {
                        logger.error("Error creating SSL socket factory", e);
                    }
                }, executorService);
            } else {
                // Send error message to the user (this part depends on your bot framework)
                logger.warn("Verification process not initiated for user: {}", userId);
            }
        }
    }
}
