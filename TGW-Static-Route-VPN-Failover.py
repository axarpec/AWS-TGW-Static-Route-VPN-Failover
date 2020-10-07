import json
import boto3
import sys
import os

PrimaryVPN = 'UP'
PrimaryVPNStatus = []
SecondaryVPN = 'DOWN'
SecondaryVPNStatus = []
CIDR = []
client = boto3.client('ec2')
# check if VPN ID vs TGW is correct or not
ActiveVPN = os.environ['ActiveVPN']
StandbyVPN = os.environ['StandbyVPN']
TransitGatewayID = os.environ['TransitGatewayID']


def lambda_handler(event, context):
    response_primary_vpn = client.describe_vpn_connections(
        VpnConnectionIds=[
            ActiveVPN,
        ]
    )
    response_secondary_vpn = client.describe_vpn_connections(
        VpnConnectionIds=[
            StandbyVPN,
        ]
    )

    if TransitGatewayID == response_primary_vpn['VpnConnections'][0]['TransitGatewayId'] == \
            response_secondary_vpn['VpnConnections'][0]['TransitGatewayId']:
        print('VPN IDs are valid')
    else:
        print('VPN IDs are not associated with TGW ID ' + TransitGatewayID)
        sys.exit('Exiting the code. Please enter the correct VPN ID which are associated with same TGW ID')

    # fetch TGW Attachment ID and check the TGW RTB for it

    response_primary_vpn = client.describe_transit_gateway_attachments(
        Filters=[
            {
                'Name': 'resource-id',
                'Values': [
                    ActiveVPN,
                ]
            },
        ],
    )
    ActiveVPN_Ass_Id = response_primary_vpn['TransitGatewayAttachments'][0]['TransitGatewayAttachmentId']

    response_secondary_vpn = client.describe_transit_gateway_attachments(
        Filters=[
            {
                'Name': 'resource-id',
                'Values': [
                    StandbyVPN,
                ]
            },
        ],
    )
    PassiveVPN_Ass_Id = response_secondary_vpn['TransitGatewayAttachments'][0]['TransitGatewayAttachmentId']
    TGWRouteTableId = response_primary_vpn['TransitGatewayAttachments'][0]['Association']['TransitGatewayRouteTableId']

    if response_primary_vpn['TransitGatewayAttachments'][0]['Association']['TransitGatewayRouteTableId'] != \
            response_primary_vpn['TransitGatewayAttachments'][0]['Association']['TransitGatewayRouteTableId']:
        print('Both VPN ' + ActiveVPN + ' ' + StandbyVPN + ' are not associated to same TGW RTB')
        sys.exit('Exiting code. Please associate both VPN to the same TGW RTB')

    # check if Primary VPN is UP or not

    response = client.describe_vpn_connections(VpnConnectionIds=[ActiveVPN])
    for i in range(0, 2):
        TunnelDetails = response['VpnConnections'][0]['VgwTelemetry'][i]
        PrimaryVPNStatus.append(TunnelDetails['Status'])
    # print(PrimaryVPNStatus)
    if PrimaryVPNStatus[0] == PrimaryVPNStatus[1] == 'DOWN':
        PrimaryVPN = 'DOWN'
        print('Primary VPN ' + ActiveVPN + ' is down')
    else:
        PrimaryVPN = 'UP'
        print('Primary VPN ' + ActiveVPN + ' is UP')

    # check if Secondary VPN is UP
    if PrimaryVPNStatus[0] == PrimaryVPNStatus[1] == 'DOWN':
        response = client.describe_vpn_connections(VpnConnectionIds=[StandbyVPN])
        for i in range(0, 2):
            TunnelDetails = response['VpnConnections'][0]['VgwTelemetry'][i]
            SecondaryVPNStatus.append(TunnelDetails['Status'])

        if SecondaryVPNStatus[0] == SecondaryVPNStatus[1] == 'DOWN':
            SecondaryVPN = 'DOWN'
            print('Secondary VPN ' + StandbyVPN + ' is down')
        else:
            SecondaryVPN = 'UP'
            print('Secondary VPN ' + StandbyVPN + ' is UP')

    # check the existing routes which are for primary VPN store the CIDR
    response_route = client.search_transit_gateway_routes(TransitGatewayRouteTableId=TGWRouteTableId,
                                                          Filters=[
                                                              {
                                                                  'Name': 'attachment.transit-gateway-attachment-id',
                                                                  'Values': [
                                                                      ActiveVPN_Ass_Id
                                                                  ]
                                                              }
                                                          ], )
    for route in range(0, len(response_route['Routes'])):
        a = response_route['Routes'][route]['DestinationCidrBlock']
        CIDR.append(a)

    response_route = client.search_transit_gateway_routes(TransitGatewayRouteTableId=TGWRouteTableId,
                                                          Filters=[
                                                              {
                                                                  'Name': 'attachment.transit-gateway-attachment-id',
                                                                  'Values': [
                                                                      PassiveVPN_Ass_Id
                                                                  ]
                                                              }
                                                          ], )
    for route in range(0, len(response_route['Routes'])):
        a = response_route['Routes'][route]['DestinationCidrBlock']
        CIDR.append(a)

#    print(CIDR)

    # If primary VPN is UP, ensure that the routes are pointing towards primary VPN
    if PrimaryVPN == 'UP':  # change it to UP for real test
        for i in CIDR:
            response = client.search_transit_gateway_routes(
                TransitGatewayRouteTableId=TGWRouteTableId,
                Filters=[
                    {
                        'Name': 'route-search.exact-match',
                        'Values': [i]
                    },
                ], )

            if response['Routes'][0]['TransitGatewayAttachments'][0]['TransitGatewayAttachmentId'] == ActiveVPN_Ass_Id:
                break
            else:
                response = client.replace_transit_gateway_route(
                    DestinationCidrBlock=i,
                    TransitGatewayRouteTableId=TGWRouteTableId,
                    TransitGatewayAttachmentId=ActiveVPN_Ass_Id,
                )
        print('Route is pointing towards ' + ActiveVPN)


    elif (PrimaryVPN == 'DOWN') and (SecondaryVPN == 'UP'):
        for i in CIDR:
            response = client.search_transit_gateway_routes(
                TransitGatewayRouteTableId=TGWRouteTableId,
                Filters=[
                    {
                        'Name': 'route-search.exact-match',
                        'Values': [i]
                    },
                ], )

            if response['Routes'][0]['TransitGatewayAttachments'][0]['TransitGatewayAttachmentId'] == PassiveVPN_Ass_Id:
                break
            else:
                response = client.replace_transit_gateway_route(
                    DestinationCidrBlock=i,
                    TransitGatewayRouteTableId=TGWRouteTableId,
                    TransitGatewayAttachmentId=PassiveVPN_Ass_Id,
                )
        print('Route is pointing towards ' + StandbyVPN)

    # when both vpn are UP
    elif (PrimaryVPN == 'UP') and (SecondaryVPN == 'UP'):
        for i in CIDR:
            response = client.search_transit_gateway_routes(
                TransitGatewayRouteTableId=TGWRouteTableId,
                Filters=[
                    {
                        'Name': 'route-search.exact-match',
                        'Values': [i]
                    },
                ], )
            print(
                CIDR[i] + 'is poinging towards ' + response['Routes'][0]['TransitGatewayAttachments'][0]['ResourceId'])

    #when both vpn are DOWN
    elif (PrimaryVPN == 'DOWN') and (SecondaryVPN == 'DOWN'):
        print('Active VPN' + ActiveVPN + ' and StandbyVPN' + StandbyVPN + ' both are down')



