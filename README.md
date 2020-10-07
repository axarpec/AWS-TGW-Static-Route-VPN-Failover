# AWS-TGW-Static-Route-VPN-Failover

This solution will help achieve following scenario :
- On-prem firewall is having VPN connection to the AWS TGW
- If CGW is having two ISP for failover in such a way that when primary ISP goes down the traffic shifts to secondary ISP and so it the VPN connection.
- If CGW is configured to have static route only or else Policy-Based VPN
- In case of static route VPN with TGW, once failover happens on secondary ISP VPN, route needs to be modified for the new VPN connection.
- this lambda code can help you automate this process.

Here is the IAM policy which is required to run this lambda code :
- Along with default role where CW log access is given, you have to edit the role to have AmazonEC2FullAccess.

Here are the Env Variable that you will have to define while deploying this Lambda code :

- ActiveVPN --> Specicy Primary VPN Connection ID
- StandbyVPN --> Specify Backup VPN Connection ID
- TransitGatewayID --> Specify TGW ID where you have associated both VPN ID.

Note : Please ensure that both VPN Connection are part of the same TGW RTB for failover to happen seamlessly.

Triger for Lambda :
- You can have CloudWatch event to run it every 5 min or 1 min.

You can use the code from the file TGW-Static-Route-VPN-Failover.py

Stay tuned for future developemt on same project.
