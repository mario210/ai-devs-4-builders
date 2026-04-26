1. Retrieve the railway task instructions by using send_railway_request.
2. The response will contain a URL to documentation. Fetch the content from that URL.
3. Analyze the documentation to find out how to activate a railway route (aktywacja trasy) named "X-01".
4. Use submit_railway_answer to send the correct JSON payload to activate the route.

Watch out for rate limits. In case of any error like 503 or 429. Wait 8 second and try again.